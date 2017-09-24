import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import sidebar as sb
import headerbar as hb
import editor
import shelve
from dialogs import notebook_dialog as nd
from dialogs import delete_dialog as dd
from database import Database
import os
import subprocess
from logger import logger as lg

class MainWindow(Gtk.Window):

    logger = lg.Logger()

    def __init__(self):
        Gtk.Window.__init__(self, title="Noted")
        self.set_border_width(5)
        self.set_size_request(1100, 900)
        self.set_resizable(False)
        # Header Bar
        hbar = hb.Headerbar()
        hbar.connect("destroy", self.close_database)
        self.set_titlebar(hbar)

        # Notebook button
        hbar.notebook_button.connect("clicked", self.create_notebook)

        # Create Button
        hbar.create_button.connect("clicked", self.create_note)

        # Save button
        hbar.save_button.connect("clicked", self.save_note)

        # Delete Button
        hbar.delete_button.connect("clicked", self.delete_note)

        #shortcuts
        self.connect("key-press-event",self.on_key_press)

        # MAIN WINDOW
        main_window = Gtk.Grid(column_homogeneous=False, column_spacing=5)

        # SIDEBAR
        self.sidebar = sb.Sidebar()
        self.sidebar.view.connect("row_activated", self.show_note)
        self.sidebar.view.connect('button-release-event',self.show_sidebar_options)
        self.sidebar.sidebar_options['new'].connect('activate',self.create_note)
        self.sidebar.sidebar_options['delete'].connect('activate',self.delete_note)
        self.sidebar.sidebar_options['restore'].connect('activate',self.restore_note)

        
        # EDITOR
        self.editor = editor.Editor(self)

        # loads the storage file and creates the dict db
        self.start_database()

        main_window.attach(self.sidebar, 0, 0, 1, 2)
        main_window.attach(self.editor, 1, 0, 2, 1)
        self.add(main_window)

    @lg.logging_decorator(logger)
    def show_sidebar_options(self,widget,event):
        if event.button == 3:
            try:
                selected_iter = self.sidebar.get_selected()
                selected = self.sidebar.store[selected_iter][0]
                parent_iter = self.sidebar.get_parent(selected_iter)
                if parent_iter != None:
                    parent = self.sidebar.store[parent_iter][0]
                else:
                    parent = None
                if parent == 'Trash' or selected == 'Trash':
                    self.sidebar.sidebar_options['new'].set_sensitive(False)
                    self.sidebar.sidebar_options['delete'].set_sensitive(True)
                    self.sidebar.sidebar_options['restore'].set_sensitive(True)
                else:
                    self.sidebar.sidebar_options['restore'].set_sensitive(False)
                    self.sidebar.sidebar_options['new'].set_sensitive(True)
                    self.sidebar.sidebar_options['delete'].set_sensitive(True)
                self.sidebar.menu.popup(None,None,None,None,event.button,event.time)
            except TypeError:
                #there was no selection when the click occured
                pass

    @lg.logging_decorator(logger)
    def create_notebook(self, widget):
        # creates a new notebook
        dialog = nd.NameDialog(self)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            name = dialog.entry.get_text()
            if name != '' and name != 'Trash':
                self.sidebar.add_notebook(name, self.notebook_id)
                self.database.create_notebook(name,self.notebook_id)
                self.notebook_id += 1
        dialog.destroy()

    @lg.logging_decorator(logger)
    def create_note(self, widget):
        if self.sidebar.add_item("New Note", self.id):
            self.editor.set_text("")
            parent_id = self.sidebar.get_id(self.sidebar.get_selected())
            self.database.create_note("New Note",'',self.id, parent_id)
            self.id += 1

    @lg.logging_decorator(logger)
    def delete_note(self, widget):
        dialog = dd.DeleteDialog(self)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            result = self.sidebar.remove_item()
            self.editor.set_text("")
            if result is not None:
                note_id, parent_id = result
                if note_id is not None:
                    self.database.delete_note(note_id)
                else:
                    self.database.delete_notebook(parent_id)
        dialog.destroy()

    @lg.logging_decorator(logger)        
    def restore_note(self,widget):
        selected = self.sidebar.get_selected()
        if self.sidebar.store[selected][0] != 'Trash':
            idd = self.sidebar.get_id(self.sidebar.get_selected())
            note = self.database.get_note(idd)
            notebook_id,notebook_name,result = self.database.restore_note(idd)
            self.sidebar.remove_item()
            if result:
                parent_iter = self.sidebar.add_notebook(notebook_name,notebook_id)
                self.sidebar.add_item(note.name,idd,parent_iter)
                self.editor.set_text("")
            else:
                #means we have to add to an existing notebook
                #this part should be moved to the sidebar module given that is processing done by it
                children = self.sidebar.store.iter_n_children(None)
                current = 0
                current_child = self.sidebar.store.iter_children(None)
                while current < children:
                    item = self.sidebar.store[current_child]
                    if item[0] == notebook_name and item[1] == notebook_id:
                        self.sidebar.add_item(note.name,idd,item.iter)
                    current_child = self.sidebar.store.iter_next(item.iter)
                    current += 1
                self.editor.set_text("")

    @lg.logging_decorator(logger)    
    def show_note(self, treeview, path, col):
        if len(path) > 1:
            parent_iter = self.sidebar.get_parent(treeview.get_selection().get_selected()[1])
            parent_id = self.sidebar.get_id(parent_iter)
            note_id = self.sidebar.get_id(path)
            content = self.database.get_note(note_id).content
            self.editor.set_text(content)
        else:
            self.editor.set_text("")
            if treeview.row_expanded(path) is False:
                treeview.expand_row(path, True)
            else:
                treeview.collapse_row(path)
    @lg.logging_decorator(logger)
    def save_note(self, event):
        path = self.sidebar.get_selected()
        # check if something was selected and that it was not a notebook
        if path is not None and len(self.sidebar.get_path(path).to_string()) > 1:
            parent = self.sidebar.get_parent(path)
            if self.sidebar.store[parent][0] != 'Trash':
                clean_text = self.editor.get_clean_text()
                if clean_text != "":
                    title = self.get_title(clean_text)

                else:
                    title = "New Note"

                content = self.editor.get_text()
                parent_iter = self.sidebar.get_parent(path)
                parent_id = self.sidebar.get_id(parent_iter)
                note_id = self.sidebar.get_id(path)
                self.database.modify_note(title,content,note_id)
                self.sidebar.modify_item(path, title)
    @lg.logging_decorator(logger)
    def start_database(self):
        path = "{}/Noted".format(GLib.get_user_data_dir())
        if not os.path.exists(path):
            subprocess.call(['mkdir', path])
        db = shelve.open("{}/database.db".format(path))
        self.database = Database()
        self.database.start_database()
        add_trash = True
        if not db:
            self.id = 1
            self.notebook_id = 1
        else:
            self.id = db['note_id']
            self.notebook_id = db['notebook_id']
        notebooks = self.database.get_notebooks()
        #we do two iterations of the notebooks to get the trash first and then the rest.
        # is there a better way ?
        for notebook in notebooks:
            if notebook.name == 'Trash':
                add_trash = False
                notebook_iter = self.sidebar.add_notebook('Trash', notebook.idd)
                notes = self.database.get_notes_from_notebook(notebook.idd)
                for note in notes:
                    self.sidebar.add_item(note.name,note.idd,notebook_iter)
        if add_trash:
            self.database.create_notebook('Trash',self.notebook_id)
            notebook_iter = self.sidebar.add_notebook('Trash', self.notebook_id)
            self.notebook_id += 1
        self.sidebar.get_trash_iter()
        for notebook in notebooks:
            if notebook.name != 'Trash':
                notebook_iter = self.sidebar.add_notebook(notebook.name, notebook.idd)
                notes = self.database.get_notes_from_notebook(notebook.idd)
                for note in notes:
                    self.sidebar.add_item(note.name,note.idd,notebook_iter)
        db.close()

    @lg.logging_decorator(logger)
    def close_database(self, event):
        path = GLib.get_user_data_dir()
        db = shelve.open("{}/Noted/database.db".format(path))
        db['note_id'] = self.id
        db['notebook_id'] = self.notebook_id
        db.close()
        self.database.close_database()
        self.hide()
        Gtk.main_quit()
    @lg.logging_decorator(logger)
    def get_title(self, content):

        content = content.lstrip()
        title_index = content.find("\n")
        if title_index < 20 and title_index != -1:
            title = content[:title_index]
        elif len(content) > 20:
            title = content[:20]
        else:
            title = content
        return title

    @lg.logging_decorator(logger)
    def on_button_clicked(self, widget, tag):

        self.editor.toggle_tag(tag, None)

    @lg.logging_decorator(logger)
    def on_key_press(self,widget,event):
        keyval = event.keyval
        keyval_name = Gdk.keyval_name(keyval)
        state = event.state
        ctrl = (state & Gdk.ModifierType.CONTROL_MASK)
        if ctrl and keyval_name == 's':
            self.save_note(None)
        elif ctrl and keyval_name == 'n':
            self.create_note(None)
        elif ctrl and keyval_name == 'k':
            self.create_notebook(None)
        elif ctrl and keyval_name == 'q':
            self.close_database(None)

def start():
    win = MainWindow()
    win.show_all()
    Gtk.main()

if __name__=='__main__':
    start()

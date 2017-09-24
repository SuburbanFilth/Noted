# Noted

[![Join the chat at https://gitter.im/elementary-os-noted/Lobby](https://badges.gitter.im/elementary-os-noted/Lobby.svg)](https://gitter.im/elementary-os-noted/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Note taking app with basic formatting (not markdown) built with Python and GTK 3.

The Trello board can be found here : https://trello.com/b/mc6cU0Mn

Any help is welcomed :)

![noted](https://github.com/mirkobrombin/Noted/raw/master/screenshot.png)

# Installation

To run the app you need :

1. SQLAlchemy, you can install it with `apt-get install python-sqlalchemy`
2. debhelper, you can get it with `apt-get install debhelper`

Afterwards follow the steps below

```
mkdir temp
cd temp
git clone https://github.com/SuburbanFilth/Noted
cd Noted
dpkg-buildpackage -us -uc
cd ../
dpkg -i *.deb
```

You should have the application installed and you can delete the temp folder.


Icons made by [Smashicons](https://www.flaticon.com/authors/smashicons) from [Flaticon](https://www.flaticon.com/) is licensed by [Creative Commons BY 3.0](http://creativecommons.org/licenses/by/3.0/).

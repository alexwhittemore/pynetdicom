## pynetdicom

Pure Python DICOM network library

Cloned from rickardholmberg's modifications at <https://code.google.com/r/rickardholmberg-pynetdicom/>

Cloned from mercurial to git:

    mkdir ~/Desktop/tmp
    cd ~/Desktop/tmp
    git clone git://repo.or.cz/fast-export.git
    git init git_repo
    cd git_repo
    ~/Desktop/fast-export/hg-fast-export.sh -r /path/to/old/mercurial_repo
    git checkout HEAD

or something like that. Must use fresh git repo. [more info](http://hivelogic.com/articles/converting-from-mercurial-to-git)

I suspect that future upstream hg commits will need to be merged using something like <http://hg-git.github.com/>. Figuring that out is a project for later.

## Change list

* Added (numerous) StorageSOPClasses (IDs found at <http://www.dicomlibrary.com/dicom/sop/>)
* Fixed a bug in applicationentity.py in the Association class which prevented PyDev from working properly (would crash on breakpoint)

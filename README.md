Gistore
=======

Gistore is a backup utility using git as a backend, and can be used to
backup arbitrary files and directories.

    Gistore = Git + Store

Create a gistore repo
---------------------

If you want to backup something, you should create a repository to
save the backups first.

    $ gistore init --repo backup.git

This will create a bare git repository named "backup.git" under the
current directory.

Prepare a backup list
---------------------

When we have a gistore repository used for backup already, we need to
prepare a backup list and tell gistore what you would like to backup.
For example if you want to backup the whole directories such as "/etc",
and "/opt/redmine/files", run:

    $ gistore add --repo backup.git /etc /opt/redmine/files

Gistore will save the backup list in a yaml file under the gistore repo
("info/gistore_backups.yml"). Before start to backup, Gistore will chdir
to the root dir ("/") and use it as worktree. Gistore will update the
repo level gitignore file ("info/exclude") as follows to exclude unwanted
files and direcoties according to the backup list.

    *
    !/etc
    !/opt
    !/opt/redmine
    !/opt/redmine/files
    !/etc/**
    !/opt/redmine/files/**

Start to backup
---------------

Run the following command to start to backup:

    $ gistore commit --repo backup.git

If there are some files you have no privileges to read, backup may fail.
Then you should run backup as root user:

    $ sudo gistore commit --repo backup.git

You can also provide a custom commit message:

    $ sudo gistore commit --repo backup.git -m "reason to backup"

Purge old backups
-----------------

Gistore will save the latest 360 commits (backups), and it maybe last
for almost one year, if you commit once per day and every day there
are changes. Old backups other than the latest 360 commits will be
purged automatically. You can define how may commits you want to
preserve.

    $ gistore config --repo backup.git increment_backup_number 30
    $ gistore config --repo backup.git full_backup_number 12

These are the default settings. The number of config variable
"increment_backup_number" means that when there are over 30 commits
in master branch, the master branch will be saved as another branch
(e.g. branch "gistore/1") and then the history of master branch will
be purged. When there are 12 such branches (defined in config variable
"full_backup_number"), the oldest one will be deleted and the history
will be purged by calling "git gc".

You may find out that all the 360 commits can be seen in commit logs of
the master branch, using command:

    $ gistore log --repo backup.git

This is because all the branches are combined together by "info/grafts",
and this file is updated automatically.

Installation
============

Install using RubyGems:

    $ gem install gistore

Or clone this repo [1] from github, and link 'bin/gistore' to your PATH.

    $ git clone git://github.com/jiangxin/gistore
    $ ln -s $(pwd)/bin/gistore ~/bin/

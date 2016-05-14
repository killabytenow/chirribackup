Chirri Backup
=============

Chirri Backup - Cheap and ugly backup tool
> Copyright (C) 2016 Gerardo Garcia Peña <killabytenow@gmail.com>

The definitive cheap and ugly backup tool.
> Written in python, sucking from its roots.
>> Unexplicable useful.

This program is a very simple backup tool. It have been designed to be as
simple as possible, avoiding complex libraries, graphical user interfaces or
stupid features.

This program is designed for keeping a local database used for minimizing
communications with a remote storage (like a cloud storage or a ssh server,
remote storage is used as a write-only storage solution and only in case of
snapshot restoration or catastrophe recovery information is read), while
minimizing space usage.

The remote storage is configurable and this program supports several back-ends.
The supported backends are:

  - Local directory storage. Backups are stored in a local filesystem. This is
    useful when using a removable disk as a backup storage or for testing.
  - Google Cloud Storage. This backend is for using GCS as remote backup
    storage solution. Using a nearline bucket is cheap and a very reliable
    solution for backups.
  - Amazon Glacier (not implemented yet).

Please note that this program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 3 of the License, or (at your option)
any later version. You should have received a copy of the GNU General Public
License along with this program in the file LICENSE. If not, see
http://www.gnu.org/licenses/.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE.

For bugs, question or insults you may contact me at the [project's
page](http://github.com/killabytenow/chirribackup/) or writing me directly to
Gerardo Garcia <killabytenow@gmail.com>.


Installation
------------

In the following sections we expose needed dependencies and how to install them.

For installing the dependencies needed you will need to install Python's pip:

	sudo apt-get install python-pip


### Basic runtime #############################################################

Nothing needed.


### Google Cloud API libraries ################################################

Execute the following call for installing the Google Cloud API wrapper for
Python (it includes the `oauth2client` and `googleapiclient` imports):

	pip install --upgrade google-api-python-client

Once you have installed the Google Cloud API libraries, you need to create a
Google Storage Bucket (preferably a nearline bucket) and configure a Service
Account in your Google Cloud console:

  1. Create a project (your-chirri-project)

  2. Create a Google Storage bucket (ex. your-chirri-bucket)

  3. [Register your application for Google Cloud Storage in Google Developers
     Console](https://console.cloud.google.com/flows/enableapi?apiid=storage_component)

  4. [Create your Service Account JSON API credentials (in the API
     Manager)](https://console.cloud.google.com/apis/credentials/wizard?api=storage_component&project=your-chirri-project)

  5. Once your Service Account JSON credentials, download them and store in a
     safe place!


Configuration and first steps
-----------------------------

Execute the following command on the directory you want to backup:

      ./chirri {your_beloved_data} db init

Before explaining more things about this command, I have to tell one useful
thing about the chirri tool: it has a simple, ugly and rudimentary but useful
help system. For invoking it you only have to add the clause `help` to your
invocation. For instance, this is the help related to the previous command:

      ./chirri - db init help
      WARNING:CHIRRI:Target directory '-' does not exist.
      db init -- initialize directory for backups

      This action creates a void database and configures it.

      Syntax:
        ... db init

      Arguments: this command does not take any argument.
      WARNING:CHIRRI:Database not opened -- nothing to commit

If you don't know what commands are available, you can execute `help` without
specifying any other command:

      ./chirri - help

Returning to the `db init` command, its mission is to create and initialize a
`__chirri__.db` database inside your directory. This database is used for
keeping track of the status of both the local and remote storage, and it stores
all the configuration parameters too.

In the first run this database can and must be initialized completely. For this
reason, this command starts a wizard that asks you for some configuration.

In the following transcription we expose a normal execution of the command
`./chirri {your_beloved_data} db init` annotated with some comments and
aclarations:

        $ chirri {your_beloved_data} db init
> The first questions establishes most basic configuration; in this moment the
> type of remote storage and the algorithm used for compressing data:

        Basic configuration
        ===================

        Storage type (local, gs) [local]?

> The `local` storage method is used for storing the backup in a directory on
> this local machine. This method is useful for making backups to external hard
> disks, understanding how this program works and even for debugging it.
> In the future I am planning to give support to other remote storage methods
> like SSH or FTP.

> In this wizard you only have to press `ENTER` to choose the default value in
> brackets.

        Storage compression (none, lzma) [lzma]?

> By default this program uses LZMA for compressing data in the remote storage.
> This is a high performance compression algorithm, but in some situations it
> may be slow; in such situations you can disable compression choosing `none`.
> Please note that this feature can be disabled in the future: new data will be
> stored using the new chosen algorithm. Old data will remain compressed using
> the old algorithm.

> In the following wizard section the specific remote storage backend asks the
> user about the parameters used for configuring it. In this example, using the
> local storage backend, it is very easy: only the target directory where
> backup will be stored is asked. If you select other backend (like `gs` --
> Google Storage) questions may be more complex and numerous:

        Backend 'Local Storage' configuration
        =====================================

        Storage directory? b

> Finally we must confirm all the configuration parameters. Press `y`.

        Confirm
        =======

        Confirm following data:
          storage_type    = Local
          compression     = lzma
          sm_local_storage_dir = /home/yuyu/b

        Continue (yes, no) [y]?
        INFO:CHIRRI:Going to initialize database
        INFO:CHIRRI:Creating database '{your_beloved_data}/__chirri__.db'.
        INFO:CHIRRI:Database created succesfully.
        INFO:CHIRRI:Commiting changes
        INFO:CHIRRI:Closing database

Once database is created you may create your first snapshot. An snapshot is a
copy of the directory `{your_beloved_data}`, stored in the temporary
`{your_beloved_data}/__chunks__/` local directory:

	$ chirri {your_beloved_data} snapshot new
	INFO:CHIRRI:Connecting to database
	INFO:CHIRRI:Connecting to database '{your_beloved_data}/__chirri__.db'.
	INFO:CHIRRI:Creating new snapshot from scratch
	INFO:CHIRRI:Starting file discovering (pass 0)
	INFO:CHIRRI:Removing lost and excluded files (pass 1)
	INFO:CHIRRI:Hashing files (pass 2)
	WARNING:CHIRRI:Storing '2007-10-30-Alexis_en_FNAC/Photo 212.jpg' uncompressed (uncompressed=76002 < lzma=76040; ratio 1.00)
	WARNING:CHIRRI:Storing '2007-10-30-Alexis_en_FNAC/Photo 213.jpg' uncompressed (uncompressed=76015 < lzma=76048; ratio 1.00)
	INFO:CHIRRI:Snapshot 1 completed -- scheduled for upload
	INFO:CHIRRI:Commiting changes
	INFO:CHIRRI:Closing database

Please note the two _WARNING_ messages: sometimes Chirri Backup may discover
that compressing requires more space than an uncompressed files (it is usually
true with very small files). In this cases this files are stored uncompressed
in the remote storage.

Existing snapshots can be listed using the `snapshot list` command:

	$ chirri {your_beloved_data} snapshot list
	INFO:CHIRRI:Connecting to database '{your_beloved_data}/__chirri__.db'.
	snapshot  status  deleted started             finished            uploaded
	--------- ------- ------- ------------------- ------------------- -------------------
	        1       4         12/05/2016 01:24:27 12/05/2016 01:24:28                None
	INFO:CHIRRI:Commiting changes
	INFO:CHIRRI:Closing database

Please note the status `4` of the snapshot with id `1`: it means that it hasn't
been uploaded yet! So we need to do one step more before having secured our
data in our remote storage: syncing.

The `sync` operation performs all the upload operations and commits some
operations on both ends (like the `delete` operations):

	$ ./chirri {your_beloved_data} sync
	INFO:CHIRRI:Connecting to database '{your_beloved_data}/__chirri__.db'.
	INFO:CHIRRI:[UPD] Snapshot 1
	INFO:CHIRRI:[UPD] 386711160c...2319c2b658
	INFO:CHIRRI:[UPD] 88b5c73720...87a86a8849
	INFO:CHIRRI:[UPD] c9ec3c810d...54a49e0602
	INFO:CHIRRI:[UPD] e9047ceaf7...b4e96c10ff
	Finished succesfully:
	  - Uploaded 1 snapshots
	  - Uploaded 4 chunks
	  - Uploaded 215804 bytes
	  - Uploaded 5 files
	INFO:CHIRRI:Commiting changes
	INFO:CHIRRI:Closing database

Once data is secured in case of requiring to restore some data is as easy as
executing the following command:

	$ ./chirri {your_beloved_data} snapshot restore 1 {your_target_dir}
	INFO:CHIRRI:Connecting to database '{your_beloved_data}/__chirri__.db'.
	INFO:CHIRRI:Restoring snapshot 1 in target path '/home/yuyu/{your_target_dir}'.
	INFO:CHIRRI:Target path '/home/yuyu/{your_target_dir}' does not exist -- creating
	INFO:CHIRRI:Commiting changes
	INFO:CHIRRI:Closing database

Or worse, all your local database (`__chirri__.db`), and disks and computers
may be destroyed. But if you keep the backup, you can rebuild the original
database and data using the following command:

	$ ./chirri your_beloved_data_rebuilt_again db rebuild
	WARNING:CHIRRI:Target directory 'your_beloved_data_rebuilt_again' does not exist.
	Basic configuration
	===================

	Storage type (local, gs) [local]? 
	Storage compression (none, lzma) [lzma]? 

	Backend 'Local Storage' configuration
	=====================================

	Storage directory? b

	Confirm
	=======

	Confirm following data:
	  storage_type    = Local
	  compression     = lzma
	  sm_local_storage_dir = /home/yuyu/b

	Continue (yes, no) [y]? 
	INFO:CHIRRI:Going to initialize database
	INFO:CHIRRI:Creating directory 'your_beloved_data_rebuilt_again'.
	INFO:CHIRRI:Creating database 'your_beloved_data_rebuilt_again/__chirri__.db'.
	INFO:CHIRRI:Database created succesfully.

	Select target snapshot
	======================

	Please choose which snapshot do you want to restore:

	  id     status  started             finished            uploaded
	  ------ ------- ------------------- ------------------- -------------------
	       1       5 12/05/2016 01:24:27 12/05/2016 01:24:28 12/05/2016 01:31:49

	Choose snapshot [1]? 
	INFO:CHIRRI:Restoring snapshot 1 in target path '/home/yuyu/your_beloved_data_rebuilt_again'.
	WARNING:CHIRRI:Target path '/home/yuyu/your_beloved_data_rebuilt_again' already exists -- continuing restoration on it
	INFO:CHIRRI:Finished succesfully.
	INFO:CHIRRI:Commiting changes
	INFO:CHIRRI:Closing database

And if you compare the old database with the recently rebuilt, only the `__chirri__db` file will differ:

	$ diff -ur test your_beloved_data_rebuilt_again
	Binary files {your_beloved_data}/__chirri__.db and {your_beloved_data_rebuilt_again}/__chirri__.db differ


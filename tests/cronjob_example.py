# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

from time import sleep
from xaux import system_lock, FsPath

system_lock(FsPath.cwd() / 'test_cronjob.lock')

print("Cronjob running.")

file = FsPath.cwd() / 'test_cronjob.txt'
file.touch()
sleep(5)
file.unlink()

print("Cronjob finished.")

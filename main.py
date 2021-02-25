"""Slow-ass disks waker

Copyright (c) 2021 Mathieu BARBE-GAYET
All Rights Reserved.
Released under the MIT license

"""
import os
import shutil

local_files_cache = {}
remote_files_cache = {}
exclusion_list = {}


def get_files(path):
    """

    :param path:
    :return:
    """
    return [file for file in os.listdir(path) if not os.path.islink(path + file)]


def get_all_elements(path):
    """

    :param path:
    :return:
    """
    # return [file for file in os.listdir(path)]
    files_names_cache = {}
    i = 0
    for file in os.listdir(path):
        if file not in exclusion_list:
            files_names_cache[i] = file
            i += 1
    return files_names_cache


def build_cache(path, file_list):
    """

    :param path:
    :param file_list:
    :return:
    """
    cache = {}
    stat_names = ["st_mode", "st_ino", "st_dev", "st_nlink", "st_uid", "st_gid", "st_size", "st_atime", "st_mtime",
                  "st_ctime"]
    # Get the attributes of each file, then stores the couple (file name : dictionary_of_the_file_attributes) in the cache
    for file in file_list:
        # If the file is not in the exclusion list we add it to the cache and return it
        if file not in exclusion_list:
            current_file_stats = os.stat(path + file)
            stats_dict = {}
            i = 0
            for value in current_file_stats:
                stats_dict[stat_names[i]] = value
                i += 1
            cache[file] = stats_dict
    return cache


def remove_from_cache(cache, files_list):
    """

    :param cache:
    :param files_list:
    :return:
    """
    return [cache.pop(file, None) for file in files_list]


def get_files_waiting_for_a_symlink(local, remote):
    """

    :param local:
    :param remote:
    :return:
    """
    return {file: remote[file] for file in set(remote) - set(local.values())}


def rename_duplicates(local_path, local, remote):
    need_to_rebuild_cache = False
    for local_file in local:
        if local_file in remote:
            print("Duplicate found! : ", local_file)
            # If the files don't have the same last edition date, we try to rename the local one to avoid a file override
            if remote[local_file]['st_mtime'] != local[local_file]['st_mtime']:
                try:
                    split = (local_file.split("."))
                    file_name = ".".join(split[0:-1])
                    file_type = split[-1]
                    os.rename(r''+str(local_path)+str(local_file), r''+str(local_path)+file_name+'.'+str(local[local_file]['st_mtime'])+"."+file_type)
                except Exception as e:
                    # If for some reason we can't rename the file, we put it on the exclusion list
                    exclusion_list.update(local_file)
                    print("Rename file: Error when parsing ", local_file, ": ", e)
                finally:
                    need_to_rebuild_cache = True
    return need_to_rebuild_cache


def delete_orphan_links(local_path, local, remote):
    for file in local:
        absolute_path_to_file = str(local_path)+str(local[file])
        if os.path.islink(absolute_path_to_file) and file not in remote:
            try:
                os.remove(absolute_path_to_file)
            except Exception as e:
                # If for some reason we can't rename the file, we put it on the exclusion list
                exclusion_list.update(file)
                print("Delete orphan link: Error when parsing ", file, ": ", e)


def get_file_list_to_copy(local, remote):
    """

    :param local:
    :param remote:
    :return:
    """
    return {file: local[file] for file in set(local) - set(remote)}


def mk_link_to_local(list_to_process, local_path, remote_path):
    """

    :param list_to_process:
    :param local_path:
    :param remote_path:
    :return:
    """
    for file in list_to_process:
        try:
            os.symlink(remote_path + file, local_path + file)
        except Exception as e:
            print("Make symlink: Error when parsing ", file, ": ", e)


def copy_to_remote(file_list_to_copy, local_path, remote_path):
    """

    :param file_list_to_copy:
    :param local_path:
    :param remote_path:
    :return:
    """
    for file in file_list_to_copy:
        try:
            shutil.copy(local_path + file, remote_path + file)
            if os.path.exists(remote_path + file):
                os.remove(local_path + file)
        except Exception as e:
            print("Copy: Error when parsing ", file, ": ", e)


def main():
    """The main function
    0/ If the cached list of remote folder's content is empty, get the list
    1/ Checks on event triggering or at fixed intervals if the local folder has the same content as the remote one.
        The comparison will be done on a cached list of the remote folder's content.
    2/ If some files are missing in the remote folder, copy it to the remote one
    3/ Then, create a link from the remote file to the local folder
    4/ Delete the original file from the local folder
    """
    local_path = "C:/users/Dope/Downloads/"
    remote_path = "D:/Downloads/"

    #
    # 0/ Check if the list is empty not done for now
    #

    # Initializes and fills a set of file names for both a local and remote dir
    local_file_list = set([])
    remote_file_list = set([])
    local_file_list.update(get_files(local_path))
    remote_file_list.update(get_files(remote_path))
    # Builds some kind of log listing each file and it's attributes
    local_files_cache.update((build_cache(local_path, local_file_list)))
    remote_files_cache.update(build_cache(remote_path, remote_file_list))

    delete_orphan_links(local_path, get_all_elements(local_path), remote_files_cache)

    #
    # 1/ Manually started: check the difference between a local folder and it's remote counterpart
    #

    # Checks if some files exist on both locations and then tries to rename it.
    # If it works for at least one file, we rebuild the cache with the current content from the local folder.
    if rename_duplicates(local_path, local_files_cache, remote_files_cache):
        local_file_list.clear()
        local_files_cache.clear()
        local_file_list.update(get_files(local_path))
        local_files_cache.update((build_cache(local_path, local_file_list)))

    files_to_copy = {}
    files_to_copy = get_file_list_to_copy(local_files_cache, remote_files_cache)

    #
    # 2/ Copy the missing files to the remote directory
    # - then removes the original file

    copy_to_remote(files_to_copy, local_path, remote_path)
    # Updates the local cache to include the newly copied files to the list of files that need a symlink in 3/
    # Removes the deleted files from the local cache list
    remote_files_cache.update(files_to_copy)
    remove_from_cache(local_files_cache, files_to_copy)

    #
    # 3/ Create a link to the local folder
    #

    # Create a list of ALL files names (w/ symlinks), then compare it with the remote folder's content

    waiting_for_a_symlink = {}
    waiting_for_a_symlink = get_files_waiting_for_a_symlink(get_all_elements(local_path), remote_files_cache)

    # Then pass the list of files that needs a symlink to the function that will create it
    mk_link_to_local(waiting_for_a_symlink, local_path, remote_path)


if __name__ == '__main__':
    main()

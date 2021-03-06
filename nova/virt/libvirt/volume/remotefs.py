# Copyright 2014 Cloudbase Solutions Srl
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import abc
import os

from oslo_concurrency import processutils
from oslo_log import log as logging
from oslo_utils import fileutils
from oslo_utils import importutils
import six

import nova.conf
from nova.i18n import _
import nova.privsep.fs
from nova import utils

LOG = logging.getLogger(__name__)

CONF = nova.conf.CONF


def mount_share(mount_path, export_path,
                export_type, options=None):
    """Mount a remote export to mount_path.

    :param mount_path: place where the remote export will be mounted
    :param export_path: path of the export to be mounted
    :export_type: remote export type (e.g. cifs, nfs, etc.)
    :options: A list containing mount options
    """
    fileutils.ensure_tree(mount_path)

    try:
        nova.privsep.fs.mount(export_type, export_path, mount_path, options)
    except processutils.ProcessExecutionError as exc:
        if 'Device or resource busy' in six.text_type(exc):
            LOG.warning("%s is already mounted", export_path)
        else:
            raise


def unmount_share(mount_path, export_path):
    """Unmount a remote share.

    :param mount_path: remote export mount point
    :param export_path: path of the remote export to be unmounted
    """
    try:
        nova.privsep.fs.umount(mount_path)
    except processutils.ProcessExecutionError as exc:
        if 'target is busy' in six.text_type(exc):
            LOG.debug("The share %s is still in use.", export_path)
        else:
            LOG.exception(_("Couldn't unmount the share %s"), export_path)


#顶层类，向下操作create_file,remove_file等操作框架（目前支持SshDriver,RsyncDriver)
#向上封装，使用户不需要感知
class RemoteFilesystem(object):
    """Represents actions that can be taken on a remote host's filesystem."""

    def __init__(self):
        #此配置默认是ssh,也可以配置为rsync,以ssh为例，要载入的类即为
        #remotefs.SshDriver
        transport = CONF.libvirt.remote_filesystem_transport
        cls_name = '.'.join([__name__, transport.capitalize()])
        cls_name += 'Driver'
        self.driver = importutils.import_object(cls_name)

    def create_file(self, host, dst_path, on_execute=None,
                    on_completion=None):
        LOG.debug("Creating file %s on remote host %s", dst_path, host)
        self.driver.create_file(host, dst_path, on_execute=on_execute,
                                on_completion=on_completion)

    def remove_file(self, host, dst_path, on_execute=None,
                    on_completion=None):
        LOG.debug("Removing file %s on remote host %s", dst_path, host)
        self.driver.remove_file(host, dst_path, on_execute=on_execute,
                                on_completion=on_completion)

    def create_dir(self, host, dst_path, on_execute=None,
                    on_completion=None):
        LOG.debug("Creating directory %s on remote host %s", dst_path, host)
        self.driver.create_dir(host, dst_path, on_execute=on_execute,
                               on_completion=on_completion)

    def remove_dir(self, host, dst_path, on_execute=None,
                    on_completion=None):
        LOG.debug("Removing directory %s on remote host %s", dst_path, host)
        self.driver.remove_dir(host, dst_path, on_execute=on_execute,
                               on_completion=on_completion)

    def copy_file(self, src, dst, on_execute=None,
                    on_completion=None, compression=True):
        LOG.debug("Copying file %s to %s", src, dst)
        self.driver.copy_file(src, dst, on_execute=on_execute,
                              on_completion=on_completion,
                              compression=compression)

#Driver的基类
@six.add_metaclass(abc.ABCMeta)
class RemoteFilesystemDriver(object):
    @abc.abstractmethod
    def create_file(self, host, dst_path, on_execute, on_completion):
        """Create file on the remote system.

        :param host: Remote host
        :param dst_path: Destination path
        :param on_execute: Callback method to store pid of process in cache
        :param on_completion: Callback method to remove pid of process from
                              cache
        """

    @abc.abstractmethod
    def remove_file(self, host, dst_path, on_execute, on_completion):
        """Removes a file on a remote host.

        :param host: Remote host
        :param dst_path: Destination path
        :param on_execute: Callback method to store pid of process in cache
        :param on_completion: Callback method to remove pid of process from
                              cache
        """

    @abc.abstractmethod
    def create_dir(self, host, dst_path, on_execute, on_completion):
        """Create directory on the remote system.

        :param host: Remote host
        :param dst_path: Destination path
        :param on_execute: Callback method to store pid of process in cache
        :param on_completion: Callback method to remove pid of process from
                              cache
        """

    @abc.abstractmethod
    def remove_dir(self, host, dst_path, on_execute, on_completion):
        """Removes a directory on a remote host.

        :param host: Remote host
        :param dst_path: Destination path
        :param on_execute: Callback method to store pid of process in cache
        :param on_completion: Callback method to remove pid of process from
                              cache
        """

    @abc.abstractmethod
    def copy_file(self, src, dst, on_execute, on_completion, compression):
        """Copy file to/from remote host.

        Remote address must be specified in format:
            REM_HOST_IP_ADDRESS:REM_HOST_PATH
        For example:
            192.168.1.10:/home/file

        :param src: Source address
        :param dst: Destination path
        :param on_execute: Callback method to store pid of process in cache
        :param on_completion: Callback method to remove pid of process from
        :param compression: If true, compress files when copying; drivers may
            ignore this if compression is not supported
        """


class SshDriver(RemoteFilesystemDriver):

    def create_file(self, host, dst_path, on_execute, on_completion):
        utils.ssh_execute(host, 'touch', dst_path,
                          on_execute=on_execute, on_completion=on_completion)

    def remove_file(self, host, dst, on_execute, on_completion):
        utils.ssh_execute(host, 'rm', dst,
                          on_execute=on_execute, on_completion=on_completion)

    def create_dir(self, host, dst_path, on_execute, on_completion):
        utils.ssh_execute(host, 'mkdir', '-p', dst_path,
                          on_execute=on_execute, on_completion=on_completion)

    def remove_dir(self, host, dst, on_execute, on_completion):
        utils.ssh_execute(host, 'rm', '-rf', dst,
                          on_execute=on_execute, on_completion=on_completion)

    #采用scp实现copy
    def copy_file(self, src, dst, on_execute, on_completion, compression):
        # As far as ploop disks are in fact directories we add '-r' argument
        processutils.execute('scp', '-r', src, dst,
                             on_execute=on_execute,
                             on_completion=on_completion)


class RsyncDriver(RemoteFilesystemDriver):

    def create_file(self, host, dst_path, on_execute, on_completion):
        with utils.tempdir() as tempdir:
            dir_path = os.path.dirname(os.path.normpath(dst_path))

            # Create target dir inside temporary directory
            local_tmp_dir = os.path.join(tempdir,
                                         dir_path.strip(os.path.sep))
            processutils.execute('mkdir', '-p', local_tmp_dir,
                                 on_execute=on_execute,
                                 on_completion=on_completion)

            # Create file in directory
            file_name = os.path.basename(os.path.normpath(dst_path))
            local_tmp_file = os.path.join(local_tmp_dir, file_name)
            processutils.execute('touch', local_tmp_file,
                                 on_execute=on_execute,
                                 on_completion=on_completion)
            RsyncDriver._synchronize_object(tempdir,
                                            host, dst_path,
                                            on_execute=on_execute,
                                            on_completion=on_completion)

    def remove_file(self, host, dst, on_execute, on_completion):
        with utils.tempdir() as tempdir:
            RsyncDriver._remove_object(tempdir, host, dst,
                                       on_execute=on_execute,
                                       on_completion=on_completion)

    def create_dir(self, host, dst_path, on_execute, on_completion):
        with utils.tempdir() as tempdir:
            dir_path = os.path.normpath(dst_path)

            # Create target dir inside temporary directory
            local_tmp_dir = os.path.join(tempdir,
                                         dir_path.strip(os.path.sep))
            processutils.execute('mkdir', '-p', local_tmp_dir,
                                 on_execute=on_execute,
                                 on_completion=on_completion)
            RsyncDriver._synchronize_object(tempdir,
                                            host, dst_path,
                                            on_execute=on_execute,
                                            on_completion=on_completion)

    def remove_dir(self, host, dst, on_execute, on_completion):
        # Remove remote directory's content
        with utils.tempdir() as tempdir:
            processutils.execute('rsync', '--archive', '--delete-excluded',
                                 tempdir + os.path.sep,
                                 utils.format_remote_path(host, dst),
                                 on_execute=on_execute,
                                 on_completion=on_completion)

            # Delete empty directory
            RsyncDriver._remove_object(tempdir, host, dst,
                                       on_execute=on_execute,
                                       on_completion=on_completion)

    @staticmethod
    def _remove_object(src, host, dst, on_execute, on_completion):
        """Removes a file or empty directory on a remote host.

        :param src: Empty directory used for rsync purposes
        :param host: Remote host
        :param dst: Destination path
        :param on_execute: Callback method to store pid of process in cache
        :param on_completion: Callback method to remove pid of process from
                              cache
        """
        processutils.execute(
            'rsync', '--archive', '--delete',
            '--include', os.path.basename(os.path.normpath(dst)),
            '--exclude', '*',
            os.path.normpath(src) + os.path.sep,
            utils.format_remote_path(host,
                                     os.path.dirname(os.path.normpath(dst))),
            on_execute=on_execute, on_completion=on_completion)

    @staticmethod
    def _synchronize_object(src, host, dst, on_execute, on_completion):
        """Creates a file or empty directory on a remote host.

        :param src: Empty directory used for rsync purposes
        :param host: Remote host
        :param dst: Destination path
        :param on_execute: Callback method to store pid of process in cache
        :param on_completion: Callback method to remove pid of process from
                              cache
        """

        # For creating path on the remote host rsync --relative path must
        # be used. With a modern rsync on the sending side (beginning with
        # 2.6.7), you can insert a dot and a slash into the source path,
        # like this:
        #   rsync -avR /foo/./bar/baz.c remote:/tmp/
        # That would create /tmp/bar/baz.c on the remote machine.
        # (Note that the dot must be followed by a slash, so "/foo/."
        # would not be abbreviated.)
        relative_tmp_file_path = os.path.join(
            src, './',
            os.path.normpath(dst).strip(os.path.sep))

        # Do relative rsync local directory with remote root directory
        processutils.execute(
            'rsync', '--archive', '--relative', '--no-implied-dirs',
            relative_tmp_file_path,
            utils.format_remote_path(host, os.path.sep),
            on_execute=on_execute, on_completion=on_completion)

    def copy_file(self, src, dst, on_execute, on_completion, compression):
        # As far as ploop disks are in fact directories we add '-r' argument
        args = ['rsync', '-r', '--sparse', src, dst]
        if compression:
            args.append('--compress')
        processutils.execute(
            *args, on_execute=on_execute, on_completion=on_completion)

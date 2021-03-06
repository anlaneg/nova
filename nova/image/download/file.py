# Copyright 2013 Red Hat, Inc.
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

from oslo_log import log as logging

import nova.conf
from nova import exception
from nova.i18n import _, _LI
import nova.image.download.base as xfer_base
import nova.virt.libvirt.utils as lv_utils


CONF = nova.conf.CONF
LOG = logging.getLogger(__name__)


#  This module extends the configuration options for nova.conf.  If the user
#  wishes to use the specific configuration settings the following needs to
#  be added to nova.conf:
#  [image_file_url]
#  filesystem = <a list of strings referencing a config section>
#
#  For each entry in the filesystem list a new configuration section must be
#  added with the following format:
#  [image_file_url:<list entry>]
#  id = <string>
#  mountpoint = <string>
#
#    id:
#        An opaque string.  In order for this module to know that the remote
#        FS is the same one that is mounted locally it must share information
#        with the glance deployment.  Both glance and nova-compute must be
#        configured with a unique matching string.  This ensures that the
#        file:// advertised URL is describing a file system that is known
#        to nova-compute
#    mountpoint:
#        The location at which the file system is locally mounted.  Glance
#        may mount a shared file system on a different path than nova-compute.
#        This value will be compared against the metadata advertised with
#        glance and paths will be adjusted to ensure that the correct file
#        file is copied.
#
#  If these values are not added to nova.conf and the file module is in the
#  allowed_direct_url_schemes list, then the legacy behavior will occur such
#  that a copy will be attempted assuming that the glance and nova file systems
#  are the same.


class FileTransfer(xfer_base.TransferBase):

    desc_required_keys = ['id', 'mountpoint']

    #取各段配置
    def _get_options(self):
        fs_dict = {}
        for fs in CONF.image_file_url.filesystems:
            group_name = 'image_file_url:' + fs
            #取配置文件中的名称为group_name的section
            conf_group = CONF[group_name]
            if conf_group.id is None:
                msg = _('The group %(group_name)s must be configured with '
                        'an id.') % {'group_name': group_name}
                raise exception.ImageDownloadModuleConfigurationError(
                    module=str(self), reason=msg)
            fs_dict[CONF[group_name].id] = CONF[group_name]
        return fs_dict

    #检查各段是否配置了id,mountpoint字段
    def _verify_config(self):
        for fs_key in self.filesystems:
            for r in self.desc_required_keys:
                fs_ent = self.filesystems[fs_key]
                if fs_ent[r] is None:
                    msg = _('The key %s is required in all file system '
                            'descriptions.')
                    LOG.error(msg)
                    raise exception.ImageDownloadModuleConfigurationError(
                        module=str(self), reason=msg)

    def _file_system_lookup(self, metadata, url_parts):
        for r in self.desc_required_keys:
            if r not in metadata:
                url = url_parts.geturl()
                msg = _('The key %(r)s is required in the location metadata '
                        'to access the url %(url)s.') % {'r': r, 'url': url}
                LOG.info(msg)
                raise exception.ImageDownloadModuleMetaDataError(
                    module=str(self), reason=msg)
        id = metadata['id']
        if id not in self.filesystems:
            LOG.info(_LI('The ID %(id)s is unknown.'), {'id': id})
            return
        fs_descriptor = self.filesystems[id]
        return fs_descriptor

    def _normalize_destination(self, nova_mount, glance_mount, path):
        if not path.startswith(glance_mount):
            msg = (_('The mount point advertised by glance: %(glance_mount)s, '
                     'does not match the URL path: %(path)s') %
                     {'glance_mount': glance_mount, 'path': path})
            raise exception.ImageDownloadModuleMetaDataError(
                module=str(self), reason=msg)
        #将path中的glance_mount修改为nova_mount,且仅变更一次
        new_path = path.replace(glance_mount, nova_mount, 1)
        return new_path

    #提供下载函数
    def download(self, context, url_parts, dst_file, metadata, **kwargs):
        self.filesystems = self._get_options()
        if not self.filesystems:
            # NOTE(jbresnah) when nothing is configured assume legacy behavior
            nova_mountpoint = '/'
            glance_mountpoint = '/'
        else:
            self._verify_config()
            #依据传入的元数据，url获知对应的文件系统描述符
            fs_descriptor = self._file_system_lookup(metadata, url_parts)
            if fs_descriptor is None:
                msg = (_('No matching ID for the URL %s was found.') %
                        url_parts.geturl())
                raise exception.ImageDownloadModuleError(reason=msg,
                                                    module=str(self))
            nova_mountpoint = fs_descriptor['mountpoint']
            glance_mountpoint = metadata['mountpoint']

        #将glance_mountpoint变更为nova_mountpoint,定位源位置
        source_file = self._normalize_destination(nova_mountpoint,
                                                  glance_mountpoint,
                                                  url_parts.path)
        lv_utils.copy_image(source_file, dst_file)
        LOG.info(_LI('Copied %(source_file)s using %(module_str)s'),
                 {'source_file': source_file, 'module_str': str(self)})


#创建可执行下载动作的handler
def get_download_handler(**kwargs):
    return FileTransfer()


#返回此download可支持的模式
def get_schemes():
    return ['file', 'filesystem']

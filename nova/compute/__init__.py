# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

from oslo_utils import importutils

# Importing full names to not pollute the namespace and cause possible
# collisions with use of 'from nova.compute import <foo>' elsewhere.
import nova.cells.opts
import nova.exception


CELL_TYPE_TO_CLS_NAME = {'api': 'nova.compute.cells_api.ComputeCellsAPI',
                         'compute': 'nova.compute.api.API',
                         None: 'nova.compute.api.API',
                        }


def _get_compute_api_class_name():
    """Returns the name of compute API class."""
    cell_type = nova.cells.opts.get_cell_type()
    return CELL_TYPE_TO_CLS_NAME[cell_type]

#通过此函数创建instance的操作api,接入instances的处理
#通过配置的cell_type,我们使用不同的api,默认使用nova.compute.api.API
def API(*args, **kwargs):
    class_name = _get_compute_api_class_name()
    return importutils.import_object(class_name, *args, **kwargs)


def HostAPI(*args, **kwargs):
    """Returns the 'HostAPI' class from the same module as the configured
    compute api
    """
    #实例化compute api处于同一模块的HostAPI类
    compute_api_class_name = _get_compute_api_class_name()
    compute_api_class = importutils.import_class(compute_api_class_name)
    class_name = compute_api_class.__module__ + ".HostAPI"
    return importutils.import_object(class_name, *args, **kwargs)


def InstanceActionAPI(*args, **kwargs):
    """Returns the 'InstanceActionAPI' class from the same module as the
    configured compute api.
    """
    compute_api_class_name = _get_compute_api_class_name()
    compute_api_class = importutils.import_class(compute_api_class_name)
    class_name = compute_api_class.__module__ + ".InstanceActionAPI"
    return importutils.import_object(class_name, *args, **kwargs)

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

"""Starter script for Nova Compute."""

import shlex
import sys

import os_vif
from oslo_log import log as logging
from oslo_privsep import priv_context
from oslo_reports import guru_meditation_report as gmr

from nova.cmd import common as cmd_common
from nova.conductor import rpcapi as conductor_rpcapi
import nova.conf
from nova import config
from nova import objects
from nova.objects import base as objects_base
from nova import service
from nova import utils
from nova import version

CONF = nova.conf.CONF
LOG = logging.getLogger('nova.compute')


#nova compute入口
def main():
    config.parse_args(sys.argv)
    logging.setup(CONF, 'nova')
    priv_context.init(root_helper=shlex.split(utils.get_root_helper()))
    utils.monkey_patch()
    objects.register_all() #载入object目录下所有对象
    # Ensure os-vif objects are registered and plugins loaded
    os_vif.initialize()

    gmr.TextGuruMeditation.setup_autorun(version)

    cmd_common.block_db_access('nova-compute')
    objects_base.NovaObject.indirection_api = conductor_rpcapi.ConductorAPI()

    #创建并加载nova-compute对应的Manager
    server = service.Service.create(binary='nova-compute',
                                    topic=CONF.compute_topic)
    service.serve(server)
    service.wait()

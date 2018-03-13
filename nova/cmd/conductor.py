#    Copyright 2012 IBM Corp.
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

"""Starter script for Nova Conductor."""

import sys

from oslo_concurrency import processutils
from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr
from oslo_reports import opts as gmr_opts

import nova.conf
from nova import config
from nova import objects
from nova import service
from nova import utils
from nova import version

CONF = nova.conf.CONF

#conductor进程
#主要工作：接受api层送来的请求，完成相关的调度工作（通过调度进程），
# 并向compute进程下发相应的创建删除任务
def main():
    config.parse_args(sys.argv)
    logging.setup(CONF, "nova")
    utils.monkey_patch()
    objects.register_all()
    gmr_opts.set_defaults(CONF)
    objects.Service.enable_min_version_cache()

    gmr.TextGuruMeditation.setup_autorun(version, conf=CONF)

    server = service.Service.create(binary='nova-conductor',
                                    topic=CONF.conductor.topic)
    workers = CONF.conductor.workers or processutils.get_worker_count()
    service.serve(server, workers=workers)
    service.wait()

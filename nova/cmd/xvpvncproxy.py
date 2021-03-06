# Copyright (c) 2010 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""XVP VNC Console Proxy Server."""

import sys

from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr
from oslo_reports import opts as gmr_opts

import nova.conf
from nova import config
from nova import service
from nova import version
from nova.vnc import xvp_proxy

CONF = nova.conf.CONF

#nova-xvpnvncproxy，基于 Java 客户端的 VNC 访问
def main():
    config.parse_args(sys.argv)
    logging.setup(config.CONF, "nova")
    gmr_opts.set_defaults(CONF)

    gmr.TextGuruMeditation.setup_autorun(version, conf=CONF)

    wsgi_server = xvp_proxy.get_wsgi_server()
    service.serve(wsgi_server)
    service.wait()

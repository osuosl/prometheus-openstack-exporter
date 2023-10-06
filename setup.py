import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="prometheus_openstack_exporter",
    version="0.0.4",
    author="Jacek Nykis",
    description="Exposes high level OpenStack metrics to Prometheus.",
    license="GPLv3",
    keywords=["prometheus", "openstack", "exporter"],
    url="https://github.com/CanonicalLtd/prometheus-openstack-exporter",
    scripts=["prometheus-openstack-exporter"],
    install_requires=["prometheus_client",
                      "python-keystoneclient<=3.21.0",
                      "python-novaclient<=15.1.1",
                      "python-neutronclient<=6.14.0",
                      "python-cinderclient<=4.3.0",
                      "keystoneauth1<=3.17.4",
                      "msgpack==0.6.1",
                      "os-client-config==1.32.0",
                      "netaddr"],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: System :: Networking :: Monitoring",
        "License :: OSI Approved :: "
            "GNU General Public License v3 or later (GPLv3+)",
    ],
)

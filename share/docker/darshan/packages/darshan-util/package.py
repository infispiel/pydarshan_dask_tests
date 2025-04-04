# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack.package import *


class DarshanUtil(AutotoolsPackage):
    """Darshan (util) is collection of tools for parsing and summarizing log
    files produced by Darshan (runtime) instrumentation. This package is
    typically installed on systems (front-end) where you intend to analyze
    log files produced by Darshan (runtime)."""

    homepage = "https://www.mcs.anl.gov/research/projects/darshan/"
    url = "https://web.cels.anl.gov/projects/darshan/releases/darshan-3.4.0.tar.gz"
    git = "https://github.com/darshan-hpc/darshan.git"

    maintainers("shanedsnyder", "carns")

    tags = ["e4s"]

    version("dxt-pthread", branch="snyder/dxt-extra-info-pthread-id")
    version("main", branch="main", submodules="True")
    version("3.4.6", sha256="092b35e7af859af903dce0c51bcb5d3901dd0d9ad79d1b2f3282692407f032ee")
    version("3.4.5", sha256="1c017ac635fab5ee0e87a6b52c5c7273962813569495cb1dd3b7cfa6e19f6ed0")
    version("3.4.4", sha256="d9c9df5aca94dc5ca3d56fd763bec2f74771d35126d61cb897373d2166ccd867")
    version("3.4.3", sha256="dca5f9f9b0ead55a8724b218071ecbb5c4f2ef6027eaade3a6477256930ccc2c")
    version("3.4.2", sha256="b095c3b7c059a8eba4beb03ec092b60708780a3cae3fc830424f6f9ada811c6b")
    version("3.4.1", sha256="77c0a4675d94a0f9df5710e5b8658cc9ef0f0981a6dafb114d0389b1af64774c")
    version("3.4.0", sha256="7cc88b7c130ec3b574f6b73c63c3c05deec67b1350245de6d39ca91d4cff0842")
    version(
        "3.4.0-pre1", sha256="57d0fd40329b9f8a51bdc9d7635b646692b341d80339115ab203357321706c09"
    )
    version("3.3.1", sha256="281d871335977d0592a49d053df93d68ce1840f6fdec27fea7a59586a84395f7")
    version("3.3.0", sha256="2e8bccf28acfa9f9394f2084ec18122c66e45d966087fa2e533928e824fcb57a")
    version(
        "3.3.0-pre2", sha256="0fc09f86f935132b7b05df981b05cdb3796a1ea02c7acd1905323691df65e761"
    )
    version(
        "3.3.0-pre1", sha256="1c655359455b5122921091bab9961491be58a5f0158f073d09fe8cc772bd0812"
    )
    version("3.2.1", sha256="d63048b7a3d1c4de939875943e3e7a2468a9034fcb68585edbc87f57f622e7f7")
    version("3.2.0", sha256="4035435bdc0fa2a678247fbf8d5a31dfeb3a133baf06577786b1fe8d00a31b7e")
    version("3.1.8", sha256="3ed51c8d5d93b4a8cbb7d53d13052140a9dffe0bc1a3e1ebfc44a36a184b5c82")
    version("3.1.7", sha256="9ba535df292727ac1e8025bdf2dc42942715205cad8319d925723fd88709e8d6")
    version("3.1.6", sha256="21cb24e2a971c45e04476e00441b7fbea63d2afa727a5cf8b7a4a9d9004dd856")
    version("3.1.0", sha256="b847047c76759054577823fbe21075cfabb478cdafad341d480274fb1cef861c")
    version("3.0.0", sha256="95232710f5631bbf665964c0650df729c48104494e887442596128d189da43e0")

    depends_on("c", type="build")  # generated
    depends_on("cxx", type="build")  # generated
    depends_on("fortran", type="build")  # generated

    variant("bzip2", default=False, description="Enable bzip2 compression")
    variant(
        "apmpi",
        default=False,
        description="Compile with AutoPerf MPI module support",
    )
    variant(
        "apxc", default=False, description="Compile with AutoPerf XC module support",
    )

    depends_on("zlib-api")
    depends_on("bzip2", when="+bzip2", type=("build", "link", "run"))
    depends_on("autoconf", type="build")
    depends_on("automake", type="build")
    depends_on("libtool", type="build")
    depends_on("m4", type="build")
    depends_on("autoconf", type="build")
    depends_on("automake", type="build")
    depends_on("libtool", type="build")
    depends_on("m4", type="build")

    @property
    def configure_directory(self):
        return "darshan-util"

    def configure_args(self):
        spec = self.spec
        extra_args = []

        extra_args.append("--with-zlib=%s" % spec["zlib-api"].prefix)
        if spec.satisfies("+apmpi"):
            if self.version < Version("3.3.2"):
                extra_args.append("--enable-autoperf-apmpi")
            else:
                extra_args.append("--enable-apmpi-mod")
        if spec.satisfies("+apxc"):
            if self.version < Version("3.3.2"):
                extra_args.append("--enable-autoperf-apxc")
            else:
                extra_args.append("--enable-apxc-mod")

        return extra_args

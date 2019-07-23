FROM fedora

RUN dnf -y install --setopt=install_weak_deps=false --setopt=tsflags=nodocs \
    --setopt=deltarpm=false --allowerasing --best --disablerepo=\*modular \
    tox python36 python37 python38 && \
    dnf -y --setopt=install_weak_deps=false --setopt=tsflags=nodocs --best\
    --setopt=deltarpm=false --allowerasing --disablerepo=\*modular update && \
    dnf clean all

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

CMD ["/usr/bin/tox"]

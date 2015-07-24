# CoreOS+Weave Bootstrap Script

This is a simple bootstrapper for [Weave](http://weave.works/) that discovers other members of a Fleet cluster and adds them to Weave's mesh.  It's an easy way to dynamically configure Weave until [libnetwork](https://github.com/docker/libnetwork) plugins make it into a stable Docker release.

### Usage

Since this script is written in Python and CoreOS doesn't have Python, the included Dockerfile will build a static binary that can be run on CoreOS.  To build the binary, build the Docker image and then run it with your installation directory mapped to `/install`:

```
docker build -t bootstrap .
docker run --rm -v /opt/bin:/install bootstrap
```

**NOTE: This script only works on Etcd currently, not Etcd2**

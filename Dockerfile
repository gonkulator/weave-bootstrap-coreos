FROM        python:2.7.10
COPY        bootstrap.py /build/
RUN         pip install fleet pyinstaller netifaces netaddr subprocess32 requests
RUN         useradd build && \
            chown -R build:build /build
WORKDIR     /build
RUN         su build -c "pyinstaller --onefile bootstrap.py"
RUN         mkdir /install
VOLUME      /install
CMD         mv /build/dist/bootstrap /install
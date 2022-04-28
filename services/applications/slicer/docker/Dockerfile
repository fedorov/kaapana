FROM no-vnc-base:latest

LABEL IMAGE="slicer"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /src
RUN mkdir -p /data

# update required for libpulse-dev
RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y libpulse-dev

# slicer-specific libraries
RUN apt-get install -y libglu1-mesa
RUN apt-get install -y libnss3
RUN apt-get install -y libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xkb1 libxkbcommon-x11-0
RUN apt-get install -y libxcb-shape0 libxcb-xinerama0 
RUN apt-get install -y libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 

# Slicer 4.11.20200930
RUN SLICER_URL="https://download.slicer.org/bitstream/60add70fae4540bf6a89bfb4" && \
  curl -k -v -s -L $SLICER_URL | tar xz -C /tmp && \
  mv /tmp/Slicer* /opt/slicer

RUN chmod -R a+w /opt/slicer

RUN mkdir -p /root/Desktop
RUN ln -s /data /root/Desktop/
WORKDIR /data

# A supervisord config is used to make the application managed
COPY files/supervisord.conf /etc/supervisor/conf.d/

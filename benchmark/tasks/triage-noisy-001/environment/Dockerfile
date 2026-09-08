FROM op06-triagebench:local
USER root
COPY seed.json /task/conversation.json
RUN mkdir -p /workspace && chown -R op06:op06 /task /workspace
USER op06


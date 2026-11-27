FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

ARG USERNAME=vscode

USER ${USERNAME}
RUN curl -sSf https://elan.lean-lang.org/elan-init.sh | \
    sh -s -- -y --default-toolchain none

ENV PATH="/home/${USERNAME}/.elan/bin:${PATH}"

USER root

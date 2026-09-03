FROM python:3.13-slim

RUN useradd --uid 65532 --create-home --shell /usr/sbin/nologin sandbox
WORKDIR /opt/sandbox
COPY fixed_factor_smoke.py /opt/sandbox/fixed_factor_smoke.py
RUN chown -R 65532:65532 /opt/sandbox
USER 65532:65532
ENTRYPOINT ["python", "/opt/sandbox/fixed_factor_smoke.py"]

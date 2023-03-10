FROM --platform=${TARGETPLATFORM:-linux/amd64} danielmichaels/playwright-v1.30.0-webkit-focal

ARG DEBIAN_FRONTEND=noninteractive

ARG ADDITIONAL_PACKAGE

RUN apt-get -qy update \
    && apt-get -qy install --no-install-recommends gcc make ${ADDITIONAL_PACKAGE} \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /ms-playwright/chromium-* \
    && rm -rf /ms-playwright/firefox-*

RUN addgroup --system app && adduser app --system --ingroup app
RUN chown app /home/app

ENV PATH=$PATH:/home/app/.local/bin

WORKDIR /home/app/

COPY --chown=app:app . .

RUN apt-get -qy update \
    && apt-get install --no-install-recommends -y python3 python3-pip python-is-python3 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps webkit

CMD ["python", "app/main.py"]

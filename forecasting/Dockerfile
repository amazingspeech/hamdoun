FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY security/ ./security/
COPY pipeline/ ./pipeline/
COPY training/ ./training/
COPY serving/ ./serving/
COPY dashboard/ ./dashboard/
COPY db/ ./db/

# Niet als root draaien: het proces heeft geen root-rechten nodig (het
# schrijft alleen naar bind-gemounte bestanden/mappen die het al via de
# hostzijde rechten krijgt), en een gecompromitteerd proces in de container
# hoeft dan niet ook nog eens root te zijn. Vaste UID (i.p.v. wat useradd
# toevallig toewijst) zodat een operator op de server host-bestanden precies
# naar deze gebruiker kan chown'en i.p.v. ze wereldschrijfbaar te moeten
# maken — zie deploy/DEPLOY.md.
RUN useradd --no-create-home --uid 10001 --shell /usr/sbin/nologin forecasting
USER forecasting

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8000"]

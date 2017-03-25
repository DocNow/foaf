FROM python:2.7

RUN mkdir /code
WORKDIR /code
ADD . /code

RUN useradd -ms /bin/bash foaf
RUN chown -R foaf:foaf /code

RUN pip install -r requirements.txt

COPY conf/supervisord.conf /usr/local/etc/supervisord.conf

RUN mkdir /var/log/flask

CMD ["/usr/local/bin/supervisord"]

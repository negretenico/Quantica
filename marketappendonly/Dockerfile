FROM alpine:latest

RUN apk --no-cache add ca-certificates
WORKDIR /root/

# Copy the pre-built binary
COPY marketappendonly .
RUN chmod +x marketappendonly

CMD ["./marketappendonly"]
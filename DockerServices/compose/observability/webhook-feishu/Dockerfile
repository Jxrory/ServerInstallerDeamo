FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /webhook-feishu .

FROM alpine:3.19
RUN adduser -D -u 10001 appuser
COPY --from=build /webhook-feishu /usr/local/bin/webhook-feishu
USER appuser
EXPOSE 9100
ENTRYPOINT ["/usr/local/bin/webhook-feishu"]

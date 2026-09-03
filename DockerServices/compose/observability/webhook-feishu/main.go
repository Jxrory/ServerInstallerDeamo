package main

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"
)

// Alertmanager webhook payload（Prometheus alertmanager 格式）。
type amWebhook struct {
	Status string `json:"status"`
	Alerts []struct {
		Status      string            `json:"status"`
		Labels      map[string]string `json:"labels"`
		Annotations map[string]string `json:"annotations"`
		StartsAt    string            `json:"startsAt"`
		EndsAt      string            `json:"endsAt"`
	} `json:"alerts"`
}

func genSign(secret string, timestamp int64) string {
	stringToSign := fmt.Sprintf("%v\n%s", timestamp, secret)
	mac := hmac.New(sha256.New, []byte(stringToSign))
	mac.Write([]byte{})
	return base64.StdEncoding.EncodeToString(mac.Sum(nil))
}

func renderText(w amWebhook) string {
	var b strings.Builder
	for _, a := range w.Alerts {
		sev := a.Labels["severity"]
		icon := "🔵"
		switch sev {
		case "warning":
			icon = "🟠"
		case "critical":
			icon = "🔴"
		}
		status := a.Status
		if w.Status == "firing" {
			status = "firing"
		} else if w.Status == "resolved" {
			status = "resolved ✅"
		}
		fmt.Fprintf(&b, "%s %s [%s]\n", icon, status, a.Labels["alertname"])
		fmt.Fprintf(&b, "服务: %s\n", a.Labels["container"])
		if s := a.Annotations["summary"]; s != "" {
			fmt.Fprintf(&b, "%s\n", s)
		}
		if d := a.Annotations["description"]; d != "" {
			fmt.Fprintf(&b, "%s\n", d)
		}
		if a.StartsAt != "" {
			fmt.Fprintf(&b, "开始: %s\n", a.StartsAt)
		}
		b.WriteString("\n")
	}
	return strings.TrimSpace(b.String())
}

func handler(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
	if err != nil {
		http.Error(w, "read body: "+err.Error(), http.StatusBadRequest)
		return
	}
	var am amWebhook
	if err := json.Unmarshal(body, &am); err != nil {
		http.Error(w, "bad json: "+err.Error(), http.StatusBadRequest)
		return
	}

	webhookURL := os.Getenv("FEISHU_WEBHOOK_URL")
	secret := os.Getenv("FEISHU_SECRET")
	text := renderText(am)

	payload := map[string]any{
		"msg_type": "text",
		"content":  map[string]any{"text": "🚨 TpaOs 监控告警\n\n" + text},
	}
	ts := time.Now().Unix()
	if secret != "" {
		payload["timestamp"] = fmt.Sprintf("%d", ts)
		payload["sign"] = genSign(secret, ts)
	}

	bodyBytes, _ := json.Marshal(payload)
	resp, err := http.Post(webhookURL, "application/json", bytes.NewReader(bodyBytes))
	if err != nil {
		log.Printf("feishu post error: %v", err)
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		log.Printf("feishu non-200: %d %s", resp.StatusCode, string(respBody))
		http.Error(w, string(respBody), resp.StatusCode)
		return
	}
	w.WriteHeader(http.StatusOK)
	w.Write(respBody)
}

func main() {
	if os.Getenv("FEISHU_WEBHOOK_URL") == "" {
		log.Fatal("FEISHU_WEBHOOK_URL is required")
	}
	addr := os.Getenv("LISTEN_ADDR")
	if addr == "" {
		addr = ":9100"
	}
	http.HandleFunc("/alert", handler)
	log.Printf("webhook-feishu listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, nil))
}

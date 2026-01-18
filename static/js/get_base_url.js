function getWsBaseUrl() {
  const protocol = location.protocol === "https:" ? "wss://" : "ws://";
  return protocol + location.host;
}

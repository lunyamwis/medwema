self.addEventListener('push', function(event) {
  const data = event.data.json();
  const options = {
    body: data.body,
    data: data,
  };

  event.waitUntil(
    self.registration.showNotification(data.head || 'Lab Notification', options)
  );

  // Tell client to play sound
  self.clients.matchAll().then(clients => {
    clients.forEach(client => client.postMessage({ playSound: true }));
  });
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url || '/'));
});

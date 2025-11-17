self.addEventListener('push', function(event) {
  let data = {};
  try {
    data = event.data.json();
  } catch (err) {
    data = { body: event.data.text() || 'New Lab Notification', head: 'Lab Alert', url: '/' };
  }

  const options = {
    body: data.body,
    data: data,
  };

  event.waitUntil(
    (async () => {
      await self.registration.showNotification(data.head || 'Lab Notification', options);

      // Tell all open clients to play the sound
      console.log("not reaching here")
      const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      clients.forEach(client => client.postMessage({ playSound: true }));
    })()
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url || '/')
  );
});

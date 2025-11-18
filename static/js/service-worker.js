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
    vibrate: [200, 100, 200],
    renotify: true,
    requireInteraction: true,
    tag: "persistent-notification",
  };
  self.clients.matchAll({ includeUncontrolled: true }).then(clients => {
      clients.forEach(c => c.postMessage({ hello: "world" }));
  });


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


self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting()); // activates SW immediately
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim()); // take control of all clients immediately
});

/* Drag-and-drop row ordering for dashboard lists that declare data-reorder-url on their <tbody>. */
(function () {
  'use strict';

  var body = document.querySelector('tbody[data-reorder-url]');
  if (!body) return;

  var status = document.getElementById('reorder-status');
  var dragged = null;

  function say(text, ok) {
    if (!status) return;
    status.textContent = text;
    status.className = 'small ' + (ok ? 'text-success' : 'text-danger');
  }

  function save() {
    var ids = Array.prototype.map.call(body.querySelectorAll('tr[data-id]'), function (row) {
      return Number(row.dataset.id);
    });
    var token = document.querySelector('[name=csrfmiddlewaretoken]').value;
    fetch(body.dataset.reorderUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
      body: JSON.stringify({ ids: ids })
    })
      .then(function (response) {
        return response.json().then(function (data) { return { ok: response.ok, data: data }; });
      })
      .then(function (result) {
        say(result.ok ? 'Order saved. The storefront now shows this order.' : result.data.detail, result.ok);
      })
      .catch(function () { say('Could not save the order. Check your connection and try again.', false); });
  }

  body.addEventListener('dragstart', function (event) {
    dragged = event.target.closest('tr[data-id]');
    if (!dragged) return;
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', dragged.dataset.id);
    dragged.classList.add('opacity-50');
  });

  body.addEventListener('dragover', function (event) {
    if (!dragged) return;
    event.preventDefault();
    var over = event.target.closest('tr[data-id]');
    if (!over || over === dragged) return;
    var rect = over.getBoundingClientRect();
    var after = event.clientY > rect.top + rect.height / 2;
    body.insertBefore(dragged, after ? over.nextSibling : over);
  });

  body.addEventListener('drop', function (event) {
    event.preventDefault();
  });

  body.addEventListener('dragend', function () {
    if (!dragged) return;
    dragged.classList.remove('opacity-50');
    dragged = null;
    save();
  });
})();

'use strict';

// Numeric JSON tokens remain text. Never pass a diner party size through Number.
function exactResponse(text) {
  const parts = [], number = /-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/y;
  let i = 0;
  while (i < text.length) {
    const start = i;
    if (text[i] === '"') {
      i++;
      while (i < text.length) {
        if (text[i] === '\\') { i += 2; continue; }
        if (text[i++] === '"') break;
      }
      parts.push(text.slice(start, i));
    } else if (text[i] === '-' || /[0-9]/.test(text[i])) {
      number.lastIndex = i;
      const match = number.exec(text);
      if (!match) throw new Error('Unreadable response');
      parts.push(JSON.stringify(match[0])); i = number.lastIndex;
    } else { parts.push(text[i++]); }
  }
  return JSON.parse(parts.join(''));
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (key === 'value' || key === 'disabled') node[key] = value;
    else node.setAttribute(key, value);
  }
  for (const child of children.flat()) if (child !== null && child !== undefined) node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  return node;
}
function field(label, id, attrs = {}) {
  const control = el('input', {id, 'data-testid': id, ...attrs});
  return {control, node: el('div', {class: 'field'}, el('label', {for: id}, label), control)};
}
function notice(parent, id, text, kind = 'error') {
  parent.replaceChildren(el('p', {class: 'notice ' + kind, 'data-testid': id, role: kind === 'error' ? 'alert' : 'status'}, text));
}
function positiveInteger(value) {
  if (!/^[0-9]+$/.test(value) || !/[1-9]/.test(value)) throw new Error('Enter a whole number of guests, at least 1.');
  return value.replace(/^0+/, '');
}
function requestKey() { return Array.from(crypto.getRandomValues(new Uint8Array(24)), byte => byte.toString(16).padStart(2, '0')).join(''); }
function dateLabel(value) {
  const date = new Date(value + 'T12:00:00');
  return isNaN(date.getTime()) ? value : date.toLocaleDateString('en', {weekday: 'long', month: 'short', day: 'numeric', year: 'numeric'});
}
function today() {
  const date = new Date(); date.setDate(date.getDate() + 1);
  return date.getFullYear() + '-' + String(date.getMonth() + 1).padStart(2, '0') + '-' + String(date.getDate()).padStart(2, '0');
}
const page = document.querySelector('#page');
let session = null;
try { session = JSON.parse(localStorage.getItem('juniper.session') || 'null'); } catch (_) { /* No retained session. */ }
function setSession(value) {
  session = value;
  try { if (value) localStorage.setItem('juniper.session', JSON.stringify(value)); else localStorage.removeItem('juniper.session'); } catch (_) { /* The active page still retains the session. */ }
  account();
}
function account() {
  const node = document.querySelector('#account'); node.replaceChildren();
  if (session) node.append(el('span', {'data-testid': 'current-user'}, session.display_name), el('button', {type: 'button', 'data-testid': 'logout-button', onclick: () => setSession(null)}, 'Sign out'));
  else node.append(el('a', {href: '/login'}, 'Sign in'), el('a', {class: 'join', href: '/signup'}, 'Create account'));
}
class Refusal extends Error {
  constructor(status, payload) { super(payload?.error?.message || 'This request could not be completed.'); this.status = status; this.code = payload?.error?.code; }
}
async function api(path, {method = 'GET', body, key, token = session?.token} = {}) {
  const headers = {'Accept': 'application/json'};
  if (token) headers.Authorization = 'Bearer ' + token;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (key) headers['Idempotency-Key'] = key;
  const response = await fetch(path, {method, headers, body, cache: 'no-store'});
  const text = await response.text(), payload = text ? exactResponse(text) : null;
  if (!response.ok) { if (response.status === 401 && path !== '/auth/login') setSession(null); throw new Refusal(response.status, payload); }
  return payload;
}
function refusalText(error) {
  return ({table_unavailable: 'That seating was just taken. Availability has been refreshed; choose another table or time.', party_exceeds_capacity: 'This seating cannot accommodate that many guests. Choose a larger table or a combined option.', cutoff_passed: 'This reservation is too close to its start time to change or cancel.', unauthenticated: 'Sign in to continue.', email_taken: 'An account already uses this email. Sign in instead.', not_found: 'We could not find this reservation for your account.'})[error.code] || error.message;
}
function tableLabels(restaurant, ids) { return ids.map(id => restaurant.tables.find(t => t.id === id)?.label || id); }
function reservationIds(reservation) { return reservation.table_ids || [reservation.table_id]; }
function idsEqual(a, b) { return a.length === b.length && a.every((id, i) => id === b[i]); }
function heading(title, copy) { return el('div', {class: 'intro'}, el('h1', {}, title), el('p', {}, copy)); }

function authScreen(signup) {
  document.title = (signup ? 'Create account' : 'Sign in') + ' — Juniper';
  const error = el('div', {'aria-live': 'polite'}), form = el('form', {class: 'auth-form', novalidate: ''});
  const prefix = signup ? 'signup' : 'login';
  const email = field('Email address', prefix + '-email', {type: 'email', autocomplete: 'email', required: ''});
  const password = field('Password', prefix + '-password', {type: 'password', autocomplete: signup ? 'new-password' : 'current-password', required: '', minlength: '8'});
  const name = signup ? field('Your name', 'signup-display-name', {autocomplete: 'name', required: ''}) : null;
  const submit = el('button', {class: 'primary', type: 'submit', 'data-testid': prefix + '-submit'}, signup ? 'Create account' : 'Sign in');
  form.append(el('h2', {}, signup ? 'Make yourself at home' : 'Welcome back'), ...(name ? [name.node] : []), email.node, password.node, submit, error,
    el('p', {}, signup ? 'Already have an account? ' : 'Joining us for the first time? ', el('a', {href: signup ? '/login' : '/signup'}, signup ? 'Sign in' : 'Create an account')));
  form.addEventListener('submit', async event => {
    event.preventDefault(); error.replaceChildren(); submit.disabled = true;
    try {
      const body = {email: email.control.value, password: password.control.value}; if (signup) body.display_name = name.control.value;
      const result = await api('/auth/' + (signup ? 'signup' : 'login'), {method: 'POST', body: JSON.stringify(body), token: null});
      setSession(result); location.assign('/');
    } catch (err) { notice(error, 'auth-error', err instanceof Refusal ? refusalText(err) : 'We could not reach the dining room. Please try again.'); }
    finally { submit.disabled = false; }
  });
  page.append(el('div', {class: 'auth-layout'}, el('div', {class: 'auth-copy'}, el('h1', {}, signup ? 'There’s a place for you.' : 'Your next evening starts here.'), el('p', {}, 'Keep your reservation close, find the right table, and leave the rest to good company.')), form));
}

function searchScreen() {
  document.title = 'Find your table — Juniper';
  const authError = el('div'), searchError = el('div'), board = el('div'), booking = el('aside', {id: 'booking', 'aria-label': 'Booking'});
  const restaurant = el('select', {id: 'restaurant-select', 'data-testid': 'restaurant-select', disabled: true}, el('option', {value: ''}, 'Loading restaurants…'));
  const date = field('When', 'date-input', {type: 'date', value: today(), required: ''});
  // Native number controls discard valid integers beyond their floating-point range.
  // Keep decimal text in the control and validate it with positiveInteger on submit.
  const party = field('Guests', 'party-size-input', {type: 'text', inputmode: 'numeric', value: '2', required: ''});
  const button = el('button', {type: 'submit', class: 'primary', 'data-testid': 'search-button', disabled: true}, 'Find a table');
  const search = el('form', {class: 'search-form', novalidate: ''}, el('div', {class: 'field restaurant-field'}, el('label', {for: 'restaurant-select'}, 'Restaurant'), restaurant), date.node, party.node, button);
  page.append(heading('An evening worth making time for.', 'Choose your company, your evening, and a table that feels right.'), search, authError, searchError, el('div', {class: 'flow'}, board, booking));
  board.append(el('div', {class: 'empty'}, el('h2', {}, 'Choose your evening'), el('p', {}, 'Search for a time, then choose your favourite spot. Combined tables keep larger parties together.')));
  let generation = 0, query = null, chosen = null, attempt = null, selectionFeedback = null, selectedParty = null, selectedButton = null;

  function clearSelection() { chosen = null; attempt = null; booking.replaceChildren(); selectedParty = null; selectedButton = null; }
  async function runSearch(preserve = false, frozen = null) {
    const mine = ++generation; searchError.replaceChildren(); authError.replaceChildren();
    if (!preserve) clearSelection();
    let request;
    try {
      request = frozen || {restaurant_id: restaurant.value, date: date.control.value, party_size: positiveInteger(party.control.value)};
      if (!request.restaurant_id || !request.date) throw new Error('Choose a restaurant and a date.');
    } catch (err) { notice(searchError, 'search-error', err.message); return; }
    query = request;
    board.replaceChildren(el('p', {class: 'notice loading', role: 'status'}, 'Finding a place for you…'));
    try {
      const [detail, availability] = await Promise.all([api('/restaurants/' + encodeURIComponent(request.restaurant_id)), api('/availability?' + new URLSearchParams(request))]);
      if (mine !== generation) return;
      renderBoard(detail, availability, request);
    } catch (err) {
      if (mine !== generation) return;
      board.replaceChildren(); notice(searchError, 'search-error', err instanceof Refusal ? refusalText(err) : 'Availability could not be loaded. Please search again.');
    }
  }
  search.addEventListener('submit', event => { event.preventDefault(); runSearch(); });
  function renderBoard(detail, availability, searched) {
    board.replaceChildren(el('div', {class: 'board-head'}, el('div', {}, el('h2', {}, detail.name), el('p', {}, dateLabel(searched.date) + ' · ' + searched.party_size + ' guests'), el('p', {}, 'Times shown in ' + detail.timezone))));
    if (!availability.slots.length) { board.append(el('div', {class: 'empty', 'data-testid': 'no-slots'}, el('h3', {}, 'No sittings on this date'), el('p', {}, 'Try another date to find your table.'))); return; }
    board.append(el('div', {class: 'legend'}, el('span', {}, el('i'), 'Available'), el('span', {}, el('i', {class: 'taken'}), 'Unavailable')));
    const grid = el('div', {'data-testid': 'availability-grid'});
    const options = detail.tables.map(table => [table.id]);
    for (const pair of detail.combinable || []) if (availability.slots.some(slot => (slot.available_options || []).some(option => idsEqual(option.table_ids, pair)))) options.push(pair);
    for (const ids of options) {
      const labels = tableLabels(detail, ids), times = el('div', {class: 'times'});
      for (const slot of availability.slots) {
        const available = ids.length === 1 ? slot.available_table_ids.includes(ids[0]) : (slot.available_options || []).some(option => idsEqual(option.table_ids, ids));
        // Pair choices exist only at offered times; singles retain unavailable cells.
        if (ids.length === 2 && !available) continue;
        const clock = slot.starts_at_local.slice(11), selected = chosen && chosen.local === slot.starts_at_local && chosen.restaurant.id === detail.id && idsEqual(chosen.ids, ids);
        times.append(el('button', {type: 'button', class: 'slot', disabled: !available, 'data-testid': 'slot-' + ids.join('+') + '-' + clock, 'data-available': String(available), 'aria-pressed': String(Boolean(selected)), 'aria-label': labels.join(' and ') + ', ' + clock + ', ' + (available ? 'available' : 'unavailable'), onclick: () => {
          if (!session) { notice(authError, 'auth-error', 'Sign in or create an account to reserve your table.'); authError.scrollIntoView({block: 'nearest'}); return; }
          chosen = {restaurant: detail, ids: [...ids], local: slot.starts_at_local, searched}; attempt = null;
          openBooking();
          for (const cell of grid.querySelectorAll('[aria-pressed]')) cell.setAttribute('aria-pressed', String(cell.dataset.testid === 'slot-' + ids.join('+') + '-' + clock));
        }}, clock));
      }
      grid.append(el('section', {class: 'table-row'}, el('div', {class: 'table-title'}, el('h3', {}, labels.join(' + ')), el('small', {}, ids.length === 2 ? 'Together, as one table' : 'Single table')), times));
    }
    board.append(grid);
  }
  function openBooking() {
    const selection = chosen;
    const guest = field('Guests at your table', 'booking-party-size', {type: 'text', inputmode: 'numeric', value: selection.searched.party_size, required: ''});
    const submit = el('button', {type: 'submit', class: 'primary', 'data-testid': 'booking-submit'}, 'Reserve this table');
    const feedback = el('div', {'aria-live': 'polite'}), confirmation = el('div');
    const form = el('form', {class: 'slip', 'data-testid': 'booking-form', novalidate: ''}, el('h2', {}, 'Your place for the evening'),
      el('p', {class: 'summary', 'data-testid': 'booking-summary'}, tableLabels(selection.restaurant, selection.ids).join(' + ') + ' · ' + selection.local.slice(11) + ' on ' + dateLabel(selection.local.slice(0, 10))),
      guest.node, submit, el('p', {class: 'hint'}, 'Your confirmation reference will appear here.'), feedback, confirmation);
    booking.replaceChildren(form); selectedParty = guest.control; selectedButton = submit; selectionFeedback = feedback;
    guest.control.addEventListener('input', () => { attempt = null; feedback.replaceChildren(); confirmation.replaceChildren(); submit.disabled = false; submit.textContent = 'Reserve this table'; });
    form.addEventListener('submit', async event => {
      event.preventDefault(); feedback.replaceChildren(); confirmation.replaceChildren();
      if (!session) { notice(feedback, 'auth-error', 'Sign in to reserve your table.'); return; }
      let partyValue;
      try { partyValue = positiveInteger(guest.control.value); } catch (err) { notice(feedback, 'booking-error', err.message); return; }
      const seating = selection.ids.length === 1 ? ',"table_id":' + JSON.stringify(selection.ids[0]) : ',"table_ids":' + JSON.stringify(selection.ids);
      const body = '{"restaurant_id":' + JSON.stringify(selection.restaurant.id) + seating + ',"starts_at_local":' + JSON.stringify(selection.local) + ',"party_size":' + partyValue + '}';
      if (!attempt || attempt.body !== body || attempt.user !== session.user_id) attempt = {body, key: requestKey(), user: session.user_id};
      const thisAttempt = attempt, token = session.token, snapshotQuery = query;
      submit.disabled = true; submit.textContent = 'Reserving…';
      try {
        const receipt = await api('/reservations', {method: 'POST', body: thisAttempt.body, key: thisAttempt.key, token});
        if (chosen !== selection || attempt !== thisAttempt) return;
        feedback.replaceChildren(); submit.textContent = 'Show this confirmation again';
        let current = null, detail = selection.restaurant;
        try { current = await api('/reservations/' + encodeURIComponent(receipt.reference), {token}); detail = await api('/restaurants/' + encodeURIComponent(current.restaurant_id)); } catch (_) { /* Receipt confirms success, but current seating could not be read. */ }
        if (chosen !== selection || attempt !== thisAttempt) return;
        const content = el('div', {class: 'confirmation', 'data-testid': 'confirmation'}, el('h3', {}, 'Your table is reserved'), el('small', {}, 'Your confirmation reference'), el('span', {class: 'reference', 'data-testid': 'confirmation-reference'}, receipt.reference));
        if (current) {
          const labels = tableLabels(detail, reservationIds(current));
          content.append(el('p', {'data-testid': 'confirmation-details'}, detail.name + ' · ' + labels.join(' + ') + ' · ' + current.starts_at_local.slice(11) + ' on ' + dateLabel(current.starts_at_local.slice(0, 10))), el('p', {'data-testid': 'confirmation-tables'}, labels.join(' + ')));
          if (current.status === 'cancelled') content.firstChild.textContent = 'This reservation is cancelled';
        } else content.append(el('p', {'data-testid': 'confirmation-details'}, 'Your reservation was saved. Look it up for the latest seating details.'));
        content.append(el('a', {href: '/lookup?reference=' + encodeURIComponent(receipt.reference)}, 'View or cancel reservation'));
        confirmation.replaceChildren(content);
        if (query === snapshotQuery) runSearch(true, snapshotQuery);
      } catch (err) {
        if (chosen !== selection || attempt !== thisAttempt) return;
        if (err instanceof Refusal) {
          notice(feedback, 'booking-error', refusalText(err)); submit.textContent = 'Reserve this table';
          if (err.code === 'table_unavailable' && query === snapshotQuery) runSearch(true, snapshotQuery);
        } else { notice(feedback, 'booking-uncertain', 'We did not receive a confirmation. Your table may already be reserved. Retry with these same details to recover your reference.', 'uncertain'); submit.textContent = 'Retry this reservation'; }
      } finally { if (chosen === selection && attempt === thisAttempt) submit.disabled = false; }
    });
    guest.control.focus({preventScroll: true});
    if (window.innerWidth < 761) booking.scrollIntoView({block: 'start', behavior: 'auto'});
  }
  api('/restaurants').then(data => {
    restaurant.replaceChildren(...data.restaurants.map(item => el('option', {value: item.id}, item.name)));
    restaurant.disabled = !data.restaurants.length; button.disabled = !data.restaurants.length;
    if (!data.restaurants.length) { restaurant.append(el('option', {value: ''}, 'No restaurants available')); board.replaceChildren(el('div', {class: 'empty'}, el('h2', {}, 'The dining room is getting ready'), el('p', {}, 'There are no restaurants available yet. Please check back soon.'))); }
  }).catch(() => { restaurant.replaceChildren(el('option', {value: ''}, 'Restaurants unavailable')); notice(searchError, 'search-error', 'We could not load the restaurants. Refresh the page to try again.'); });
}

function lookupScreen() {
  document.title = 'Your reservation — Juniper';
  const reference = field('Confirmation reference', 'lookup-reference-input', {autocomplete: 'off', value: new URLSearchParams(location.search).get('reference') || ''});
  const button = el('button', {type: 'submit', class: 'primary', 'data-testid': 'lookup-submit'}, 'Find reservation');
  const feedback = el('div', {'aria-live': 'polite'}), detailBox = el('div');
  const form = el('form', {class: 'lookup-form'}, reference.node, button);
  page.append(el('div', {class: 'lookup'}, el('h1', {}, 'Your evening, at a glance.'), el('p', {}, 'Enter your confirmation reference to see the latest details or cancel your reservation.'), form, feedback, detailBox));
  let generation = 0;
  async function lookup() {
    const mine = ++generation; feedback.replaceChildren(); detailBox.replaceChildren();
    notice(feedback, 'lookup-loading', 'Finding your reservation…', 'loading');
    try {
      const record = await api('/reservations/' + encodeURIComponent(reference.control.value.trim()));
      const restaurant = await api('/restaurants/' + encodeURIComponent(record.restaurant_id));
      if (mine !== generation) return;
      feedback.replaceChildren();
      const labels = tableLabels(restaurant, reservationIds(record));
      const card = el('section', {class: 'detail', 'data-testid': 'reservation-detail'}, el('span', {class: 'status ' + record.status, 'data-testid': 'reservation-status'}, record.status),
        el('h2', {}, restaurant.name), el('p', {}, dateLabel(record.starts_at_local.slice(0, 10)) + ' at ' + record.starts_at_local.slice(11)),
        el('p', {'data-testid': 'reservation-tables'}, labels.join(' + ')), el('p', {}, record.party_size + ' guests'), el('p', {}, 'Reference: ' + record.reference));
      if (record.status === 'confirmed') {
        const cancel = el('button', {type: 'button', class: 'secondary', 'data-testid': 'reservation-cancel-button'}, 'Cancel reservation');
        cancel.addEventListener('click', async () => {
          cancel.disabled = true; feedback.replaceChildren();
          try { await api('/reservations/' + encodeURIComponent(record.reference) + '/cancel', {method: 'POST', body: '{}'}); if (mine === generation) await lookup(); }
          catch (err) { if (mine === generation) notice(feedback, 'reservation-error', err instanceof Refusal ? refusalText(err) : 'The cancellation response was not received. Look up the reservation to check its status.'); }
          finally { cancel.disabled = false; }
        });
        card.append(cancel);
      }
      detailBox.replaceChildren(card);
    } catch (err) { if (mine === generation) notice(feedback, 'reservation-error', err instanceof Refusal ? refusalText(err) : 'We could not load your reservation. Please try again.'); }
  }
  form.addEventListener('submit', event => { event.preventDefault(); lookup(); });
  if (reference.control.value && session) lookup();
}

account();
for (const link of document.querySelectorAll('nav a')) if (link.getAttribute('href') === location.pathname) link.setAttribute('aria-current', 'page');
if (location.pathname === '/signup') authScreen(true);
else if (location.pathname === '/login') authScreen(false);
else if (location.pathname === '/lookup') lookupScreen();
else searchScreen();

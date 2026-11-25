(() => {
  'use strict';

  const CART_KEY = 'phygaplanet_shop_cart_v1';
  const money = (amount) => `${Number(amount || 0).toLocaleString('fa-IR')} تومان`;
  const normalize = (value) => String(value || '').toLocaleLowerCase('fa-IR').replace(/[ي]/g, 'ی').replace(/[ك]/g, 'ک').trim();

  function readCart() {
    try {
      const value = JSON.parse(localStorage.getItem(CART_KEY) || '[]');
      return Array.isArray(value) ? value : [];
    } catch (error) {
      return [];
    }
  }

  function saveCart(cart) {
    try {
      localStorage.setItem(CART_KEY, JSON.stringify(cart));
    } catch (error) {
      showToast('ذخیره سبد خرید در این مرورگر ممکن نیست.');
    }
  }

  function trackCartAdd(productId, quantity) {
    const endpoint = document.body?.dataset.cartTrackUrl;
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
    if (!endpoint || !csrf || !window.fetch) return;
    fetch(endpoint, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({ product_id: productId, quantity })
    }).catch(() => { /* Cart UX remains available if analytics is temporarily offline. */ });
  }

  function cartQuantity(cart = readCart()) {
    return cart.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
  }

  function updateCartCount() {
    const count = cartQuantity();
    document.querySelectorAll('[data-cart-count]').forEach((node) => {
      node.textContent = count.toLocaleString('fa-IR');
      node.setAttribute('aria-label', `${count} کالا در سبد خرید`);
    });
  }

  function showToast(message) {
    const region = document.querySelector('[data-toast-region]');
    if (!region) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    region.appendChild(toast);
    window.setTimeout(() => toast.remove(), 2800);
  }

  function addProduct(button) {
    const id = String(button.dataset.productId || '').trim();
    if (!id) {
      showToast('شناسه کالا برای افزودن به سبد مشخص نشده است.');
      return;
    }
    const quantitySelector = button.dataset.quantitySource;
    const quantityInput = quantitySelector ? document.querySelector(quantitySelector) : null;
    const quantity = Math.max(1, Number(quantityInput?.value || 1));
    const product = {
      id,
      name: button.dataset.productName || 'کالای PhygaPlanet',
      price: Number(button.dataset.productPrice || 0),
      image: button.dataset.productImage || '',
      url: button.dataset.productUrl || '#'
    };
    const cart = readCart();
    const existing = cart.find((item) => String(item.id) === id);
    if (existing) {
      existing.quantity = Number(existing.quantity || 0) + quantity;
      existing.name = product.name;
      existing.price = product.price;
      existing.image = product.image;
      existing.url = product.url;
    } else {
      cart.push({ ...product, quantity });
    }
    saveCart(cart);
    trackCartAdd(id, quantity);
    updateCartCount();
    showToast(`«${product.name}» به سبد خرید اضافه شد.`);
  }

  function setupQuantityControl() {
    document.querySelectorAll('[data-quantity-control]').forEach((control) => {
      const input = control.querySelector('[data-quantity-value]');
      const minus = control.querySelector('[data-quantity-minus]');
      const plus = control.querySelector('[data-quantity-plus]');
      if (!input) return;
      const getBounds = () => ({ min: Number(input.min || 1), max: Number(input.max || 99) });
      minus?.addEventListener('click', () => {
        const bounds = getBounds();
        input.value = Math.max(bounds.min, Number(input.value || 1) - 1);
      });
      plus?.addEventListener('click', () => {
        const bounds = getBounds();
        input.value = Math.min(bounds.max, Number(input.value || 1) + 1);
      });
      input.addEventListener('change', () => {
        const bounds = getBounds();
        input.value = Math.min(bounds.max, Math.max(bounds.min, Number(input.value || 1)));
      });
    });
  }

  function setupCatalog() {
    const root = document.querySelector('[data-catalog]');
    if (!root) return;
    const grid = root.querySelector('[data-product-grid]');
    if (!grid) return;
    const search = root.querySelector('[data-product-search]');
    const categories = [...root.querySelectorAll('[data-category-filter]')];
    const stock = root.querySelector('[data-stock-filter]');
    const price = root.querySelector('[data-price-filter]');
    const priceLabel = root.querySelector('[data-price-label]');
    const sort = root.querySelector('[data-sort-products]');
    const resultCount = root.querySelector('[data-result-count]');
    const noResults = root.querySelector('[data-no-results]');

    const applyFilters = () => {
      const query = normalize(search?.value);
      const category = categories.find((item) => item.checked)?.value || 'all';
      const onlyStock = Boolean(stock?.checked);
      const maxPrice = Number(price?.value || Number.MAX_SAFE_INTEGER);
      const cards = [...grid.querySelectorAll('[data-product-card]')];
      let visible = 0;
      cards.forEach((card) => {
        const name = normalize(card.dataset.name);
        const cardCategory = card.dataset.category || '';
        const cardPrice = Number(card.dataset.price || 0);
        const cardStock = Number(card.dataset.stock || 0);
        const matches = (!query || name.includes(query)) && (category === 'all' || cardCategory === category) && (!onlyStock || cardStock > 0) && cardPrice <= maxPrice;
        card.hidden = !matches;
        if (matches) visible += 1;
      });
      if (resultCount) resultCount.textContent = visible.toLocaleString('fa-IR');
      if (noResults) noResults.hidden = visible > 0;
      if (priceLabel) priceLabel.textContent = money(maxPrice);
      applySort();
    };

    const applySort = () => {
      const mode = sort?.value || 'recommended';
      const cards = [...grid.querySelectorAll('[data-product-card]')];
      cards.sort((a, b) => {
        if (mode === 'price-asc') return Number(a.dataset.price || 0) - Number(b.dataset.price || 0);
        if (mode === 'price-desc') return Number(b.dataset.price || 0) - Number(a.dataset.price || 0);
        if (mode === 'name') return normalize(a.dataset.name).localeCompare(normalize(b.dataset.name), 'fa');
        return 0;
      });
      cards.forEach((card) => grid.appendChild(card));
    };

    [search, stock, price, sort, ...categories].filter(Boolean).forEach((control) => {
      control.addEventListener(control === search ? 'input' : 'change', applyFilters);
    });
    search?.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter') return;
      event.preventDefault();
      const endpoint = root.dataset.catalogUrl;
      if (!endpoint) return;
      const url = new URL(endpoint, window.location.origin);
      if (search.value.trim()) url.searchParams.set('q', search.value.trim());
      const category = categories.find((item) => item.checked)?.value || 'all';
      if (category !== 'all') url.searchParams.set('type', category);
      if (stock?.checked) url.searchParams.set('available', '1');
      window.location.assign(url.toString());
    });
    root.querySelectorAll('[data-filter-reset]').forEach((button) => {
      button.addEventListener('click', () => {
        if (search) search.value = '';
        if (stock) stock.checked = false;
        if (price) price.value = price.max;
        if (sort) sort.value = 'recommended';
        categories.forEach((item) => { item.checked = item.value === 'all'; });
        applyFilters();
      });
    });
    applyFilters();
  }

  function createCartItem(item) {
    const article = document.createElement('article');
    article.className = 'cart-item';

    const image = document.createElement('div');
    image.className = 'cart-item-image';
    if (item.image) {
      const img = document.createElement('img');
      img.src = item.image;
      img.alt = item.name;
      image.appendChild(img);
    } else {
      image.textContent = '♫';
    }

    const info = document.createElement('div');
    info.className = 'cart-item-info';
    const title = document.createElement('h3');
    title.textContent = item.name;
    const note = document.createElement('p');
    note.textContent = 'یادگاری موسیقی از PhygaPlanet';
    const actions = document.createElement('div');
    actions.className = 'cart-item-actions';
    const qty = document.createElement('div');
    qty.className = 'cart-qty';
    const minus = document.createElement('button');
    minus.type = 'button'; minus.textContent = '−'; minus.setAttribute('aria-label', 'کم کردن تعداد');
    const number = document.createElement('span');
    number.textContent = Number(item.quantity).toLocaleString('fa-IR');
    const plus = document.createElement('button');
    plus.type = 'button'; plus.textContent = '+'; plus.setAttribute('aria-label', 'زیاد کردن تعداد');
    minus.addEventListener('click', () => changeQuantity(item.id, -1));
    plus.addEventListener('click', () => changeQuantity(item.id, 1));
    qty.append(minus, number, plus);
    const remove = document.createElement('button');
    remove.type = 'button'; remove.className = 'cart-remove'; remove.textContent = 'حذف';
    remove.addEventListener('click', () => removeProduct(item.id));
    actions.append(qty, remove);
    info.append(title, note, actions);

    const price = document.createElement('div');
    price.className = 'cart-item-price';
    price.textContent = money(Number(item.price) * Number(item.quantity));
    article.append(image, info, price);
    return article;
  }

  function renderCart() {
    const root = document.querySelector('[data-cart-root]');
    if (!root) return;
    const cart = readCart();
    const itemsNode = root.querySelector('[data-cart-items]');
    const emptyNode = root.querySelector('[data-cart-empty]');
    const summaryCount = root.querySelector('[data-cart-items-count]');
    const subtotal = cart.reduce((sum, item) => sum + Number(item.price || 0) * Number(item.quantity || 0), 0);
    if (itemsNode) {
      itemsNode.replaceChildren(...cart.map(createCartItem));
    }
    if (emptyNode) emptyNode.hidden = cart.length !== 0;
    if (itemsNode) itemsNode.hidden = cart.length === 0;
    if (summaryCount) summaryCount.textContent = `${cartQuantity(cart).toLocaleString('fa-IR')} کالا`;
    root.querySelectorAll('[data-cart-subtotal], [data-cart-total]').forEach((node) => { node.textContent = money(subtotal); });
    const checkout = root.querySelector('[data-checkout-link]');
    if (checkout) {
      checkout.setAttribute('aria-disabled', cart.length === 0 ? 'true' : 'false');
      checkout.classList.toggle('is-disabled', cart.length === 0);
    }
  }

  function changeQuantity(id, delta) {
    const cart = readCart();
    const item = cart.find((entry) => String(entry.id) === String(id));
    if (!item) return;
    item.quantity = Number(item.quantity || 1) + delta;
    if (item.quantity < 1) {
      saveCart(cart.filter((entry) => String(entry.id) !== String(id)));
    } else {
      saveCart(cart);
      if (delta > 0) trackCartAdd(id, delta);
    }
    updateCartCount();
    renderCart();
  }

  function removeProduct(id) {
    saveCart(readCart().filter((item) => String(item.id) !== String(id)));
    updateCartCount();
    renderCart();
    showToast('کالا از سبد خرید حذف شد.');
  }

  function renderCheckoutSummary() {
    const node = document.querySelector('[data-checkout-items]');
    if (!node) return;
    const cart = readCart();
    const total = cart.reduce((sum, item) => sum + Number(item.price || 0) * Number(item.quantity || 0), 0);
    node.replaceChildren();
    if (!cart.length) {
      const empty = document.createElement('p');
      empty.className = 'muted-note';
      empty.textContent = 'سبد خرید خالی است. ابتدا کالاها را انتخاب کن.';
      node.appendChild(empty);
    } else {
      cart.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'checkout-mini-item';
        const name = document.createElement('span');
        name.textContent = `${item.name} × ${Number(item.quantity).toLocaleString('fa-IR')}`;
        const price = document.createElement('b');
        price.textContent = money(Number(item.price) * Number(item.quantity));
        row.append(name, price);
        node.appendChild(row);
      });
    }
    const totalNode = document.querySelector('[data-checkout-total]');
    if (totalNode) totalNode.textContent = money(total);
  }

  function setupCheckout() {
    const form = document.querySelector('[data-checkout-form]');
    if (!form) return;
    form.addEventListener('submit', (event) => {
      const cart = readCart();
      if (!cart.length) {
        event.preventDefault();
        showToast('سبد خرید خالی است؛ ابتدا یک کالا انتخاب کن.');
        return;
      }
      let payload = form.querySelector('input[name="cart_payload"]');
      if (!payload) {
        payload = document.createElement('input');
        payload.type = 'hidden';
        payload.name = 'cart_payload';
        form.appendChild(payload);
      }
      // Send identifiers and quantities only. The backend reloads all prices and stock.
      payload.value = JSON.stringify(cart.map((item) => ({ id: item.id, quantity: item.quantity })));
      if (form.action.endsWith('#')) {
        event.preventDefault();
        showToast('برای ثبت سفارش واقعی، این فرم باید به view ثبت سفارش Django متصل شود.');
      }
    });
  }

  function setupMobileMenu() {
    const toggle = document.querySelector('[data-menu-toggle]');
    const nav = document.querySelector('[data-mobile-nav]');
    if (!toggle || !nav) return;
    toggle.addEventListener('click', () => {
      const isOpen = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!isOpen));
      nav.hidden = isOpen;
    });
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-cart-add]');
    if (button && !button.disabled) addProduct(button);
    const coupon = event.target.closest('[data-coupon-apply]');
    if (coupon) {
      const message = document.querySelector('[data-coupon-message]');
      if (message) message.textContent = 'اعتبارسنجی کد تخفیف پس از اتصال بک‌اند فعال می‌شود.';
    }
  });

  document.addEventListener('DOMContentLoaded', () => {
    setupMobileMenu();
    setupQuantityControl();
    setupCatalog();
    updateCartCount();
    renderCart();
    renderCheckoutSummary();
    setupCheckout();
  });
})();

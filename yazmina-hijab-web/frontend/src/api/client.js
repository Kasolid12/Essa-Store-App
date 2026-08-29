/**
 * Yazmina Hijab Web — API Client.
 *
 * Thin wrapper around fetch() for all API calls.
 * Uses httpOnly cookies for auth (no Bearer token in headers).
 */

const API_BASE = '/api';

class ApiClient {
  /**
   * Generic fetch with JSON handling.
   * @param {string} path - API path (e.g. '/auth/login')
   * @param {object} options - fetch options
   * @param {object} extra - { silent401: true } to skip redirect on 401
   * @returns {Promise<any>} parsed JSON response
   */
  async request(path, options = {}, { silent401 = false } = {}) {
    const url = `${API_BASE}${path}`;
    const config = {
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',  // send cookies
      ...options,
    };

    const res = await fetch(url, config);

    if (res.status === 401) {
      if (silent401) {
        // Let caller handle 401 gracefully (e.g. AuthProvider initial check)
        throw new Error('Not authenticated');
      }
      // For other calls, redirect to login
      window.location.href = '/login';
      throw new Error('Not authenticated');
    }

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${res.status}`);
    }

    // Some endpoints return 204 No Content
    if (res.status === 204) return null;
    return res.json();
  }

  // ── Auth ──────────────────────────────────────────────────────────
  async login(username, password) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  }

  async logout() {
    return this.request('/auth/logout', { method: 'POST' });
  }

  async getMe() {
    // silent401: don't redirect — AuthProvider handles it gracefully
    return this.request('/auth/me', {}, { silent401: true });
  }

  // ── Dashboard ─────────────────────────────────────────────────────
  async getDashboard(mulai = '', akhir = '') {
    const params = new URLSearchParams();
    if (mulai) params.set('mulai', mulai);
    if (akhir) params.set('akhir', akhir);
    return this.request(`/dashboard?${params.toString()}`);
  }

  async getDashboardTrend(months = 6) {
    return this.request(`/dashboard/trend?months=${months}`);
  }

  async getDashboardStats() {
    return this.request('/dashboard/stats');
  }

  // ── Profit Simulation ─────────────────────────────────────────
  async listProfitBatches() {
    return this.request('/profit/batches');
  }

  async analyzeProfitBatch(kode) {
    return this.request(`/profit/analyze/${encodeURIComponent(kode)}`);
  }

  async toggleProfitStatus(kode) {
    return this.request(`/profit/toggle-status/${encodeURIComponent(kode)}`, { method: 'POST' });
  }

  async saveProfitHistory(kode) {
    return this.request(`/profit/save-history?kode_produksi=${encodeURIComponent(kode)}`, { method: 'POST' });
  }

  async listProfitHistory() {
    return this.request('/profit/history');
  }

  async listTarif() {
    return this.request('/profit/tarif');
  }

  async saveTarif(data) {
    return this.request('/profit/tarif', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ── Stock Manager ─────────────────────────────────────────────
  async listStockSkus(search = '') {
    const qs = search ? `?search=${encodeURIComponent(search)}` : '';
    return this.request(`/stock/skus${qs}`);
  }

  async exportStock(items, mode) {
    const res = await fetch(`${API_BASE}/stock/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ items, mode }),
    });
    if (!res.ok) throw new Error('Export gagal');
    const blob = await res.blob();
    const disposition = res.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename="(.+)"/);
    const filename = match ? match[1] : `export_${Date.now()}.xlsx`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    return { filename };
  }

  // ── SKU ───────────────────────────────────────────────────────────
  async listSku(params = {}) {
    const qs = new URLSearchParams();
    if (params.search) qs.set('search', params.search);
    if (params.kategori) qs.set('kategori', params.kategori);
    return this.request(`/sku?${qs.toString()}`);
  }

  async createSku(data) {
    return this.request('/sku', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSku(id, data) {
    return this.request(`/sku/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteSku(id) {
    return this.request(`/sku/${id}`, { method: 'DELETE' });
  }

  async listSkuCategories() {
    return this.request('/sku/categories/list');
  }

  // ── Persons ──────────────────────────────────────────────────────
  async listPersonTypes() {
    return this.request('/persons/types');
  }

  async listPersons(params = {}) {
    const qs = new URLSearchParams();
    if (params.search) qs.set('search', params.search);
    if (params.person_type) qs.set('person_type', params.person_type);
    return this.request(`/persons?${qs.toString()}`);
  }

  async createPerson(data) {
    return this.request('/persons', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updatePerson(id, data) {
    return this.request(`/persons/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deletePerson(id) {
    return this.request(`/persons/${id}`, { method: 'DELETE' });
  }

  // ── Modal Operasional ─────────────────────────────────────────
  async listModalOperasional(params = {}) {
    const qs = new URLSearchParams();
    if (params.search) qs.set('search', params.search);
    if (params.jenis) qs.set('jenis', params.jenis);
    if (params.date_from) qs.set('date_from', params.date_from);
    if (params.date_to) qs.set('date_to', params.date_to);
    return this.request(`/modal-operasional?${qs.toString()}`);
  }

  async createModalOperasional(data) {
    return this.request('/modal-operasional', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateModalOperasional(id, data) {
    return this.request(`/modal-operasional/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteModalOperasional(id) {
    return this.request(`/modal-operasional/${id}`, { method: 'DELETE' });
  }

  async summaryModalOperasional(params = {}) {
    const qs = new URLSearchParams();
    if (params.date_from) qs.set('date_from', params.date_from);
    if (params.date_to) qs.set('date_to', params.date_to);
    return this.request(`/modal-operasional/summary?${qs.toString()}`);
  }

  async listJenisOperasional() {
    return this.request('/modal-operasional/jenis');
  }

  // ── Pengeluaran Offline ──────────────────────────────────────────
  async listPengeluaranOffline(params = {}) {
    const qs = new URLSearchParams();
    if (params.search) qs.set('search', params.search);
    if (params.date_from) qs.set('date_from', params.date_from);
    if (params.date_to) qs.set('date_to', params.date_to);
    return this.request(`/pengeluaran-offline?${qs.toString()}`);
  }

  async createPengeluaranOffline(data) {
    return this.request('/pengeluaran-offline', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updatePengeluaranOffline(id, data) {
    return this.request(`/pengeluaran-offline/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deletePengeluaranOffline(id) {
    return this.request(`/pengeluaran-offline/${id}`, { method: 'DELETE' });
  }

  async summaryPengeluaranOffline(params = {}) {
    const qs = new URLSearchParams();
    if (params.date_from) qs.set('date_from', params.date_from);
    if (params.date_to) qs.set('date_to', params.date_to);
    return this.request(`/pengeluaran-offline/summary?${qs.toString()}`);
  }

  // ── Hasil Cutting ─────────────────────────────────────────────
  async listHasilCutting(params = {}) {
    const qs = new URLSearchParams();
    if (params.date_from) qs.set('date_from', params.date_from);
    if (params.date_to) qs.set('date_to', params.date_to);
    return this.request(`/hasil-cutting?${qs.toString()}`);
  }

  async createHasilCutting(data) {
    return this.request('/hasil-cutting', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateHasilCutting(id, data) {
    return this.request(`/hasil-cutting/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteHasilCutting(id) {
    return this.request(`/hasil-cutting/${id}`, { method: 'DELETE' });
  }

  // ── Distribusi Cutting ─────────────────────────────────────────
  async listDistribusiCutting(params = {}) {
    const qs = new URLSearchParams();
    if (params.date_from) qs.set('date_from', params.date_from);
    if (params.date_to) qs.set('date_to', params.date_to);
    return this.request(`/distribusi-cutting?${qs.toString()}`);
  }

  async createDistribusiCutting(data) {
    return this.request('/distribusi-cutting', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateDistribusiCutting(id, data) {
    return this.request(`/distribusi-cutting/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteDistribusiCutting(id) {
    return this.request(`/distribusi-cutting/${id}`, { method: 'DELETE' });
  }

  // ── Hutang ──────────────────────────────────────────────────────
  async listHutang(params = {}) {
    const qs = new URLSearchParams();
    if (params.tipe_hutang) qs.set('tipe_hutang', params.tipe_hutang);
    if (params.status) qs.set('status', params.status);
    if (params.date_from) qs.set('date_from', params.date_from);
    if (params.date_to) qs.set('date_to', params.date_to);
    return this.request(`/hutang?${qs.toString()}`);
  }

  async createHutang(data) {
    return this.request('/hutang', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateHutang(id, data) {
    return this.request(`/hutang/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteHutang(id) {
    return this.request(`/hutang/${id}`, { method: 'DELETE' });
  }

  async summaryHutang(params = {}) {
    const qs = new URLSearchParams();
    if (params.tipe_hutang) qs.set('tipe_hutang', params.tipe_hutang);
    return this.request(`/hutang/summary?${qs.toString()}`);
  }

  async listPayments(debtId) {
    return this.request(`/hutang/${debtId}/payments`);
  }

  async createPayment(debtId, data) {
    return this.request(`/hutang/${debtId}/payments`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async batchPay(data) {
    return this.request('/hutang/batch-pay', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ── Gaji ──────────────────────────────────────────────────────
  async listGaji(params = {}) {
    const qs = new URLSearchParams();
    if (params.tipe) qs.set('tipe', params.tipe);
    if (params.date_from) qs.set('date_from', params.date_from);
    if (params.date_to) qs.set('date_to', params.date_to);
    return this.request(`/gaji?${qs.toString()}`);
  }

  async getGaji(id) {
    return this.request(`/gaji/${id}`);
  }

  async createGaji(data) {
    return this.request('/gaji', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateGaji(id, data) {
    return this.request(`/gaji/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteGaji(id) {
    return this.request(`/gaji/${id}`, { method: 'DELETE' });
  }

  async listGajiTipe() {
    return this.request('/gaji/tipe');
  }

  async getBonLama(personId) {
    return this.request(`/gaji/bon-lama/${personId}`);
  }

  async importExcelPenjahit(file) {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${API_BASE}/gaji/import-excel-penjahit`, {
      method: 'POST',
      body: fd,
      credentials: 'include',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async importExcelPengsup(file) {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${API_BASE}/gaji/import-excel-pengsup`, {
      method: 'POST',
      body: fd,
      credentials: 'include',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async importAbsensi(file) {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${API_BASE}/gaji/import-absensi`, {
      method: 'POST',
      body: fd,
      credentials: 'include',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async savePasukan(data) {
    return this.request('/gaji/save-pasukan', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async editKaryawan(data) {
    return this.request('/gaji/edit-karyawan', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getAttendance(runId) {
    return this.request(`/gaji/attendance/${runId}`);
  }

  // ── Bon ─────────────────────────────────────────────────────────
  async listBonBalances() {
    return this.request('/bon/balances');
  }

  async listBonMovements(params = {}) {
    const qs = new URLSearchParams();
    if (params.person_id) qs.set('person_id', params.person_id);
    if (params.date_from) qs.set('date_from', params.date_from);
    if (params.date_to) qs.set('date_to', params.date_to);
    return this.request(`/bon/movements?${qs.toString()}`);
  }

  async createBonMovement(data) {
    return this.request('/bon/move', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ── Clients ────────────────────────────────────────────────────
  async listClients(params = {}) {
    const qs = new URLSearchParams();
    if (params.search) qs.set('search', params.search);
    return this.request(`/clients?${qs.toString()}`);
  }

  async createClient(data) {
    return this.request('/clients', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateClient(id, data) {
    return this.request(`/clients/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteClient(id) {
    return this.request(`/clients/${id}`, { method: 'DELETE' });
  }

  // ── Invoice & Piutang ──────────────────────────────────────────
  async listInvoiceClients() {
    return this.request('/invoice/clients');
  }

  async getInvoiceCombined(clientRef) {
    return this.request(`/invoice/combined/${clientRef}`);
  }

  async getInvoiceSummary(clientRef) {
    return this.request(`/invoice/summary/${clientRef}`);
  }

  async createInvoiceDeposit(clientRef, data) {
    return this.request(`/invoice/deposit/${clientRef}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteInvoicePayment(paymentId) {
    return this.request(`/invoice/payment/${paymentId}`, { method: 'DELETE' });
  }
}

export const api = new ApiClient();

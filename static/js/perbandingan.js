function updateTabelPerbandingan(mataUang) {
  if (mataUang === '-') {
    document.getElementById('uangperbandingan_rataPerubahan').textContent = '-';
    document.getElementById('uangperbandingan_tren').textContent = '-';
    document.getElementById('uangperbandingan_kenaikanMax').textContent = '-';
    document.getElementById('uangperbandingan_penurunanMax').textContent = '-';
    document.getElementById('uangperbandingan_volatilitas').textContent = '-';
    document.getElementById('uangperbandingan_hariNaik').textContent = '-';
    document.getElementById('uangperbandingan_hariTurun').textContent = '-';
    document.getElementById('uangperbandingan_trenNaik').textContent = '-';
    document.getElementById('uangperbandingan_trenTurun').textContent = '-';
    document.getElementById('uangperbandingan_persenUntung').textContent = '-';
    return;
  }
  const data = window.dataPerbandingan[mataUang];
  if (!data) return;
  document.getElementById('uangperbandingan_rataPerubahan').textContent = data['Rata-rata Perubahan (%)'];
  document.getElementById('uangperbandingan_tren').textContent = data['Tren Dominan'];
  document.getElementById('uangperbandingan_kenaikanMax').textContent = data['Kenaikan Max(%)'];
  document.getElementById('uangperbandingan_penurunanMax').textContent = data['Penurunan Max(%)'];
  document.getElementById('uangperbandingan_volatilitas').textContent = data['Volatilitas(%)'];
  document.getElementById('uangperbandingan_hariNaik').textContent = data['Jumlah Hari Naik'];
  document.getElementById('uangperbandingan_hariTurun').textContent = data['Jumlah Hari Turun'];
  document.getElementById('uangperbandingan_trenNaik').textContent = data['Durasi Tren Naik Terpanjang'];
  document.getElementById('uangperbandingan_trenTurun').textContent = data['Durasi Tren Turun Terpanjang'];
  document.getElementById('uangperbandingan_persenUntung').textContent = data['Persentase Hari Untung(%)'];
}

document.addEventListener('DOMContentLoaded', function() {
  var dropdown = document.getElementById('dropdownPerbandingan');
  var thPembanding = document.getElementById('thPembanding');
  if (dropdown && thPembanding) {
    dropdown.addEventListener('change', function() {
      var mataUang = this.value;
      thPembanding.textContent = mataUang === '-' ? '-' : mataUang + '/IDR';
      updateTabelPerbandingan(mataUang);
    });
    
    thPembanding.textContent = '-';
    updateTabelPerbandingan('-');
  }
});

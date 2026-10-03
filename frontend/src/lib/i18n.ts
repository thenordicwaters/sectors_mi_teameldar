import { writable } from 'svelte/store';

export type Locale = 'en' | 'id';

export const locale = writable<Locale>('en');

const STORAGE_KEY = 'idx-locale';

export function initLocale(): void {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === 'id' || saved === 'en') locale.set(saved);
}

export function setLocale(next: Locale): void {
  locale.set(next);
  localStorage.setItem(STORAGE_KEY, next);
}

const en = {
  'lang.switch': 'Language',
  'nav.discover': 'Discover',
  'nav.unusual': 'Unusual activity',
  'nav.compare': 'Compare',
  'footer.sources':
    'Sectors is the primary source for company data, fundamentals, and foreign flow. Yahoo Finance supplements historical price and volume data.',
  'footer.disclaimer': 'For information and analysis only. Not investment advice.',

  'home.kicker': 'Market intelligence',
  'home.title': 'Find stocks worth investigating.',
  'home.ready':
    '{count} Indonesian stocks. Narrow the market, then open a stock to see its score, signals, and supporting evidence.',
  'home.intro':
    'Narrow the Indonesian market, then open a stock to see its score, signals, and supporting evidence.',
  'home.searchLabel': 'Ticker or company',
  'home.searchPlaceholder': 'Search ticker or company',
  'home.sector': 'Sector',
  'home.subsector': 'Subsector',
  'home.signal': 'Signal',
  'home.sort': 'Sort by',
  'home.minScore': 'Minimum overall score',
  'home.any': 'Any',
  'home.unusualOnly': 'Unusual activity only',
  'home.all': 'All',
  'home.loadingTitle': 'Loading the market universe…',
  'home.loadingDetail':
    'Scores, signals, and unusual-activity flags are calculated from the local snapshot.',
  'home.errorTitle': 'The screener could not be loaded.',
  'home.emptyTitle': 'No stocks match these filters.',
  'home.emptyDetail':
    'Try widening the sector selection or clearing the score and signal filters.',
  'home.clearFilters': 'Clear filters',
  'home.clear': 'Clear',
  'home.inScope': '{count} stocks in {scope}',
  'home.market': 'the Indonesian market',
  'home.ticker': 'Ticker',
  'home.company': 'Company',
  'home.overall': 'Overall',
  'home.signalCol': 'Signal',
  'home.anomaly': 'Unusual activity',
  'home.showMore': 'Show more',
  'home.sortOverall': 'Overall score',
  'home.sortQuality': 'Quality',
  'home.sortValue': 'Value',
  'home.sortMomentum': 'Momentum',
  'home.sortFlow': 'Foreign flow',

  'signal.mover': 'Price mover',
  'signal.fifty_two_week_high': '52-week high',
  'signal.foreign_accumulation': 'Foreign accumulation',
  'signal.insider_buying': 'Insider buying',

  'ihsg.kicker': 'Jakarta Composite Index',
  'ihsg.title': 'IHSG',
  'ihsg.loading': 'Loading the latest IHSG session…',
  'ihsg.error': 'The IHSG chart could not be loaded.',
  'ihsg.unavailable': 'Yahoo Finance did not return an IHSG session.',
  'ihsg.today': 'Trading session {date}.',
  'ihsg.weekend':
    'The exchange is closed today. The latest available session is {date}.',
  'ihsg.earlier':
    'The latest session available from Yahoo Finance is {date}.',
  'ihsg.priorHigh': 'Previous-day high {price}',
  'ihsg.priorDate': 'H-1 · {date}',

  'chart.h1': 'Previous-day high',
  'chart.above':
    'The latest close is above the previous day’s high.',
  'chart.below':
    'The latest close is below the previous day’s high.',
  'chart.same':
    'The latest close is at the previous day’s high.',
  'chart.explain':
    'H-1 means the previous trading day. The dashed line marks that session’s highest price, making it easy to see whether the latest close moved beyond it.',
  'chart.empty':
    'Intraday price data is unavailable. The previous day’s high is still shown when provided by Yahoo Finance.',
  'chart.source': 'Yahoo Finance',
  'chart.sectors': 'Sectors',
  'chart.loading': 'Loading closing prices from Sectors…',
  'chart.error': 'The price chart could not be loaded.',
  'chart.session':
    'Latest completed close: {date}. Today’s session is not included.',
  'chart.rangeLabel': 'Date range',
  'chart.emptyHistory': 'No closing prices are available for this range.',

  'quote.checking': 'Checking the latest session…',
  'quote.asOf': 'As of',
  'quote.today': 'This is today’s trading session.',
  'quote.weekend':
    'The exchange is closed today, so this is the latest completed trading session.',
  'quote.earlier':
    'This is the latest trading session available from Yahoo Finance.',
  'quote.unavailable':
    'The latest Yahoo Finance price is unavailable. The figure below is the most recent Sectors close in the saved snapshot.',
  'quote.snapshot':
    'Scores still use the Sectors snapshot from {date}, with a closing price of {price}. This snapshot is not refreshed daily.',
  'quote.whyTitle': 'Why the previous page showed an older price',
  'quote.whyBody':
    'The headline price comes from the latest daily close provided by Yahoo Finance, with the session date shown beside it. Scores and signals still use the saved Sectors snapshot. A snapshot is a point-in-time copy of the market, so its closing price can remain unchanged for several days while the live market moves. On Saturday and Sunday, the exchange does not publish a new trading session, so the latest available session remains the previous trading day.',

  'stock.back': '← Discover stocks',
  'stock.loading': 'Opening the research brief…',
  'stock.errorTitle': 'This stock is not available.',
  'stock.sectorMissing': 'Sector unavailable',
  'stock.overall': 'Overall',
  'stock.rank': 'Universe rank {rank}',
  'stock.scores': 'Analysis scores',
  'stock.compare': 'Compare',
  'stock.scoring': 'Calculating this stock’s score against the universe…',
  'stock.scoreError': 'Method scores are unavailable.',
  'stock.plain': 'In plain language',
  'stock.whyInteresting': 'Why this stock stands out',
  'stock.noneInteresting':
    'No signal or unusual-activity flag is currently attached to this stock in the saved data.',
  'stock.viewDetails': 'View details',
  'stock.why': 'Why',
  'stock.tests': 'Tests',
  'stock.evidence': 'Evidence',
  'stock.missing': 'Missing data: {fields}.',
  'stock.methodology': 'Methodology',
  'stock.sourceLine': 'Source: {source}',
  'stock.version': 'version {version}',
  'stock.notApplied': 'Not applied',
  'stock.noScore': 'No score',
  'stock.whyUnusual': 'Why is this unusual?',
  'stock.flaggedFrom': 'Flagged from',
  'stock.deviations': '{count} standard deviations',
  'stock.figures': 'Underlying figures',
  'stock.figuresHelp':
    'The scores above are calculated from these cached inputs.',
  'stock.marketCap': 'Market cap',
  'stock.pe': 'P/E',
  'stock.pb': 'P/B',
  'stock.foreign': 'Net foreign inflow',
  'stock.weights': 'Weights used:',
  'stock.quality': 'Quality',
  'stock.value': 'Value',
  'stock.momentum': 'Momentum',
  'stock.flow': 'Foreign flow',
  'stock.pillars':
    'The overall score is the weighted average of the available pillars. Missing pillars are excluded and the remaining weights are rescaled. Stocks with fewer than three available pillars are left unranked.',
  'stock.calculated': 'Calculated from Sectors + Yahoo Finance',
  'stock.howOverall': 'How the overall score is calculated',
  'stock.chartTitle': 'Price',
  'stock.momentumNote':
    'Yahoo Finance price history is used when the momentum card identifies Yahoo Finance as its source.',

  'method.piotroski.title': 'Piotroski',
  'method.piotroski.beginner':
    'A nine-point checklist about a company’s financial condition: is it profitable, is profit converting into cash, and has the balance sheet improved from the previous year? The score counts how many tests pass. It provides a structured way to examine financial strength rather than relying on price alone.',
  'method.piotroski.methodology':
    'Nine yes-or-no tests compared with the previous fiscal year. The score is the number of tests passed. At least six tests must be computable. Financial companies are excluded and use Financial Quality instead.',
  'method.piotroski.headline': 'F-score {score} of 9.',

  'method.magic_formula.title': 'Magic Formula',
  'method.magic_formula.beginner':
    'A framework for looking at profitability and valuation together. It considers how efficiently a company generates profit from its capital and how much investors are paying for those earnings. A higher score means both measures rank more favorably relative to other stocks.',
  'method.magic_formula.methodology':
    'Earnings yield and return on capital are ranked and combined into a percentile, where 100 is the highest-ranked result. In this cache, earnings yield is 1/P/E and return on capital is ROE. Financials and utilities are excluded. The value pillar then re-ranks the result among sector peers when enough peers are available.',
  'method.magic_formula.headline':
    'Earnings yield {ey}, return on capital {roc}. Percentile {pct}.',

  'method.momentum.title': 'Momentum',
  'method.momentum.beginner':
    'Measures how a stock’s price has performed over a longer period while leaving out the most recent month. This score uses the change from twelve months ago to one month ago, then ranks that return against other Indonesian stocks. Excluding the latest month reduces the influence of the most recent price move.',
  'method.momentum.methodology':
    '12-1 momentum is the return from twelve months ago to one month ago, then percentile-ranked across the universe. When that history is unavailable, the daily close change in the snapshot is ranked as a one-day fallback.',
  'method.momentum.twelve':
    '12-1 return {ret}. Percentile {pct}.',
  'method.momentum.daily':
    'Ranked on the daily move in the snapshot: {ret}. Percentile {pct}.',

  'method.foreign_flow.title': 'Foreign Flow',
  'method.foreign_flow.beginner':
    'Measures foreign buying or selling relative to foreign trading activity. A higher score indicates stronger net foreign buying compared with other stocks in the universe. This adds market-flow context that is not visible in standard financial statements.',
  'method.foreign_flow.methodology':
    'Net foreign buying divided by foreign turnover, combined with the stock’s turnover relative to the universe, then percentile-ranked. This is a strength score and is separate from the unusual-activity Z-score.',
  'method.foreign_flow.headline':
    'Net foreign flow is {ratio} of foreign turnover. Percentile {pct}.',

  'method.financials_quality.title': 'Financial Quality',
  'method.financials_quality.beginner':
    'Banks and other financial companies are assessed using metrics that are more relevant to their business model, particularly the return generated on shareholders’ equity. The general-company checklist is not used for these businesses, so this method takes its place.',
  'method.financials_quality.methodology':
    'Used only for banks and other financial companies. Available metrics are percentile-ranked within the financial sector. Net interest margin and non-performing loans are often missing in this cache, so ROE may be the only available input.',
  'method.none': 'This method returned no result.',
  'method.notApplied': 'This method is not applied to this stock.',
  'method.noScore': 'There is not enough data to calculate a score.',
  'method.fallback': 'Score from the cached universe.',

  'piotroski.roa_positive': 'ROA > 0',
  'piotroski.cfo_positive': 'Cash flow from operations > 0',
  'piotroski.roa_increased': 'ROA higher than the previous year',
  'piotroski.accrual': 'Cash flow from operations > net income',
  'piotroski.leverage_decreased':
    'Long-term debt ratio lower than the previous year',
  'piotroski.current_ratio_increased':
    'Current ratio higher than the previous year',
  'piotroski.no_new_shares': 'No new shares issued',
  'piotroski.gross_margin_increased':
    'Gross margin higher than the previous year',
  'piotroski.asset_turnover_increased':
    'Asset turnover higher than the previous year',
  'piotroski.pass': 'pass',
  'piotroski.fail': 'fail',
  'piotroski.unknown': 'insufficient data',

  'signal.mover.method':
    'Flagged when the absolute daily closing-price change is at least 5%. The change comes from the Sectors universe snapshot.',
  'signal.fifty_two_week_high.method':
    'Flagged from the Sectors 52-week-high tag, or when the close is within 2% of the 52-week high in the Yahoo Finance price overlay.',
  'signal.foreign_accumulation.method':
    'Flagged when net foreign inflow is at least Rp 1 billion and at least 15% of foreign turnover on the latest cached Sectors foreign-flow day.',
  'signal.insider_buying.method':
    'Flagged from an insider-buying filing provided by Sectors within the cached filing window.',

  'anomaly.volume.high': 'Volume spike',
  'anomaly.volume.low': 'Volume drought',
  'anomaly.flow.high': 'Foreign inflow spike',
  'anomaly.flow.low': 'Foreign outflow spike',
  'anomaly.volume.referenceHigh':
    'Trading volume in this session is unusually high compared with the stock’s own history.',
  'anomaly.volume.referenceLow':
    'Trading volume in this session is unusually low compared with the stock’s own history.',
  'anomaly.flow.referenceHigh':
    'Foreign buying is unusually strong compared with other stocks on the same day.',
  'anomaly.flow.referenceLow':
    'Foreign selling is unusually strong compared with other stocks on the same day.',
  'anomaly.volume.method':
    'Standard score of the latest cached session against the stock’s trailing volume baseline. The latest session is excluded from the baseline. Yahoo Finance provides the historical volume data.',
  'anomaly.flow.method':
    'Robust standard score of net foreign inflow divided by the stock’s average traded value, measured across stocks on the same day. Sectors provides foreign-flow data; Yahoo Finance provides traded-value inputs.',
  'anomaly.volume.reason':
    'Volume of {observed} is {z} standard deviations {direction} the stock’s own average of {baseline}.',
  'anomaly.flow.reason':
    'Foreign flow on this day is {multiple}× the stock’s usual traded value and {z} standard deviations {direction} the market median.',
  'anomaly.above': 'above',
  'anomaly.below': 'below',
  'anomaly.z': 'Z-score',

  'unusual.kicker': 'Market discovery',
  'unusual.title': 'What’s unusual in the market?',
  'unusual.intro':
    'Volume is compared with each stock’s own history. Foreign flow is compared with other stocks on the same day.',
  'unusual.sector': 'Sector',
  'unusual.subsector': 'Subsector',
  'unusual.kind': 'Unusual activity',
  'unusual.all': 'All',
  'unusual.volume': 'Volume',
  'unusual.flow': 'Foreign flow',
  'unusual.loading': 'Scanning for unusual activity…',
  'unusual.errorTitle': 'Unusual activity could not be loaded.',
  'unusual.emptyTitle': 'No unusual activity matches these filters.',
  'unusual.emptyDetail':
    'Try all sectors, or switch between volume and foreign flow.',
  'unusual.count': '{count} unusual flags',
  'unusual.in': 'in {name}',
  'unusual.spanLabel': 'As of',
  'unusual.spanHelp':
    'Each card is dated to the trading session being measured. When the sessions differ, the date range above covers every card shown in the list.',
  'unusual.why': 'Why is this unusual?',
  'unusual.latestVolume': 'Latest volume',
  'unusual.flowVsValue': 'Flow vs traded value',
  'unusual.ownAverage': 'Own-history average',
  'unusual.sameDayMedian': 'Same-day median',
  'unusual.flaggedFrom': 'Flagged from',
  'unusual.method': 'Methodology',
  'unusual.showMore': 'Show more',
  'unusual.how': 'How unusual activity is measured',
  'unusual.noteVolume':
    'Volume uses the latest Yahoo Finance session for the stock and compares it with the stock’s earlier sessions. The date on the card is the measured session.',
  'unusual.noteFlow':
    'Foreign flow uses a cached Sectors trading day and compares the stock with other stocks on that same day. The date on the card is the measured day.',

  'compare.kicker': 'Side by side',
  'compare.title': 'Compare two or three stocks.',
  'compare.intro':
    'Compare scores, signals, and underlying characteristics side by side. Open a ticker to see the supporting evidence.',
  'compare.first': 'First',
  'compare.second': 'Second',
  'compare.third': 'Third, optional',
  'compare.submit': 'Compare',
  'compare.loading': 'Loading research briefs…',
  'compare.errorTitle': 'Those stocks could not be compared.',
  'compare.idleTitle': 'Add at least two tickers.',
  'compare.idleDetail':
    'Each column keeps its own scores, signals, and available data.',
  'compare.overall': 'Overall',
  'compare.signals': 'Signals',
  'compare.anomaly': 'Unusual activity',
  'compare.footnote':
    'Calculated from Sectors, with Yahoo Finance price history where a stock’s momentum uses it. Open a ticker to inspect the evidence.',
  'compare.loaded': 'loaded',
  'compare.unavailable': 'Unavailable',

  'field.return_12m': '12-month return',
  'field.return_1m': '1-month return',
  'field.twelve_minus_one': '12-1 momentum',
  'field.daily_return': 'Daily return',
  'field.source': 'Return used',
  'field.ranked_value': 'Ranked value',
  'field.earnings_yield': 'Earnings yield',
  'field.return_on_capital': 'Return on capital',
  'field.earnings_yield_rank': 'Earnings-yield rank',
  'field.return_on_capital_rank': 'Return-on-capital rank',
  'field.combined_rank': 'Combined rank',
  'field.percentile': 'Percentile',
  'field.net_foreign_inflow': 'Net foreign inflow',
  'field.foreign_turnover': 'Foreign turnover',
  'field.net_ratio': 'Net / foreign turnover',
  'field.relative_volume': 'Turnover vs universe median',
  'field.return_on_equity': 'ROE',
  'field.net_interest_margin': 'Net interest margin',
  'field.non_performing_loans': 'Non-performing loans',
  'field.roe_percentile': 'ROE percentile',
  'field.nim_percentile': 'NIM percentile',
  'field.npl_percentile': 'NPL percentile',
  'field.parts_used': 'Metrics used',
  'field.tests_computable': 'Tests computable',
  'field.tests_passed': 'Tests passed',
  'field.f_score': 'F-score',
  'source.twelve_minus_one': '12-month return through 1 month ago',
  'source.daily_return': 'Daily price change in the snapshot',
} as const;

const id: Record<keyof typeof en, string> = {
  'lang.switch': 'Bahasa',
  'nav.discover': 'Temukan saham',
  'nav.unusual': 'Aktivitas tidak biasa',
  'nav.compare': 'Bandingkan',
  'footer.sources':
    'Sectors adalah sumber utama untuk data perusahaan, fundamental, dan arus dana asing. Yahoo Finance melengkapi data harga dan volume historis.',
  'footer.disclaimer':
    'Untuk informasi dan analisis saja. Bukan saran investasi.',

  'home.kicker': 'Intelijen pasar',
  'home.title': 'Temukan saham yang layak diteliti.',
  'home.ready':
    'Jelajahi {count} saham Indonesia. Persempit pasar, lalu buka saham untuk melihat skor, sinyal, dan bukti pendukungnya.',
  'home.intro':
    'Persempit pasar Indonesia, lalu buka saham untuk melihat skor, sinyal, dan bukti pendukungnya.',
  'home.searchLabel': 'Kode atau perusahaan',
  'home.searchPlaceholder': 'Cari kode atau perusahaan',
  'home.sector': 'Sektor',
  'home.subsector': 'Subsektor',
  'home.signal': 'Sinyal',
  'home.sort': 'Urutkan berdasarkan',
  'home.minScore': 'Skor keseluruhan minimum',
  'home.any': 'Apa saja',
  'home.unusualOnly': 'Hanya aktivitas tidak biasa',
  'home.all': 'Semua',
  'home.loadingTitle': 'Memuat semesta pasar…',
  'home.loadingDetail':
    'Skor, sinyal, dan aktivitas tidak biasa dihitung dari snapshot lokal.',
  'home.errorTitle': 'Penyaring saham tidak dapat dimuat.',
  'home.emptyTitle': 'Tidak ada saham yang cocok dengan filter ini.',
  'home.emptyDetail':
    'Coba perluas pilihan sektor atau hapus filter skor dan sinyal.',
  'home.clearFilters': 'Hapus filter',
  'home.clear': 'Hapus',
  'home.inScope': '{count} saham di {scope}',
  'home.market': 'pasar Indonesia',
  'home.ticker': 'Kode',
  'home.company': 'Perusahaan',
  'home.overall': 'Keseluruhan',
  'home.signalCol': 'Sinyal',
  'home.anomaly': 'Aktivitas tidak biasa',
  'home.showMore': 'Tampilkan lagi',
  'home.sortOverall': 'Skor keseluruhan',
  'home.sortQuality': 'Kualitas',
  'home.sortValue': 'Nilai',
  'home.sortMomentum': 'Momentum',
  'home.sortFlow': 'Arus dana asing',

  'signal.mover': 'Pergerakan harga',
  'signal.fifty_two_week_high': 'Tertinggi 52 minggu',
  'signal.foreign_accumulation': 'Akumulasi asing',
  'signal.insider_buying': 'Pembelian orang dalam',

  'ihsg.kicker': 'Indeks Harga Saham Gabungan',
  'ihsg.title': 'IHSG',
  'ihsg.loading': 'Memuat sesi IHSG terbaru…',
  'ihsg.error': 'Grafik IHSG tidak dapat dimuat.',
  'ihsg.unavailable':
    'Yahoo Finance tidak mengembalikan data sesi IHSG.',
  'ihsg.today': 'Sesi perdagangan {date}.',
  'ihsg.weekend':
    'Bursa tutup hari ini. Sesi terakhir yang tersedia adalah {date}.',
  'ihsg.earlier':
    'Sesi terakhir yang tersedia dari Yahoo Finance adalah {date}.',
  'ihsg.priorHigh': 'Tertinggi hari sebelumnya {price}',
  'ihsg.priorDate': 'H-1 · {date}',

  'chart.h1': 'Tertinggi hari sebelumnya',
  'chart.above':
    'Penutupan terakhir berada di atas harga tertinggi hari sebelumnya.',
  'chart.below':
    'Penutupan terakhir berada di bawah harga tertinggi hari sebelumnya.',
  'chart.same':
    'Penutupan terakhir berada pada level yang sama dengan harga tertinggi hari sebelumnya.',
  'chart.explain':
    'H-1 berarti hari bursa sebelumnya. Garis putus-putus menandai harga tertinggi pada sesi tersebut, sehingga mudah terlihat apakah penutupan terakhir melewatinya.',
  'chart.empty':
    'Data harga intrahari tidak tersedia. Harga tertinggi hari sebelumnya tetap ditampilkan jika tersedia di Yahoo Finance.',
  'chart.source': 'Yahoo Finance',
  'chart.sectors': 'Sectors',
  'chart.loading': 'Memuat harga penutupan dari Sectors…',
  'chart.error': 'Grafik harga tidak dapat dimuat.',
  'chart.session':
    'Penutupan terakhir: {date}. Sesi hari ini tidak termasuk.',
  'chart.rangeLabel': 'Rentang tanggal',
  'chart.emptyHistory':
    'Tidak ada harga penutupan yang tersedia untuk rentang ini.',

  'quote.checking': 'Memeriksa sesi terbaru…',
  'quote.asOf': 'Per',
  'quote.today': 'Ini adalah sesi perdagangan hari ini.',
  'quote.weekend':
    'Bursa tutup hari ini, jadi ini adalah sesi perdagangan terakhir yang selesai.',
  'quote.earlier':
    'Ini adalah sesi perdagangan terbaru yang tersedia dari Yahoo Finance.',
  'quote.unavailable':
    'Harga terbaru dari Yahoo Finance tidak tersedia. Angka di bawah adalah harga penutupan Sectors terbaru yang tersimpan di snapshot.',
  'quote.snapshot':
    'Skor tetap menggunakan snapshot Sectors tanggal {date}, dengan harga penutupan {price}. Snapshot ini tidak diperbarui setiap hari.',
  'quote.whyTitle':
    'Mengapa halaman sebelumnya menampilkan harga yang lebih lama',
  'quote.whyBody':
    'Harga utama berasal dari penutupan harian terbaru yang diberikan Yahoo Finance, dengan tanggal sesi ditampilkan di sampingnya. Skor dan sinyal tetap menggunakan snapshot Sectors yang tersimpan. Snapshot adalah salinan kondisi pasar pada satu waktu tertentu, sehingga harga penutupannya dapat tetap sama selama beberapa hari sementara harga pasar terus bergerak. Pada Sabtu dan Minggu, bursa tidak menerbitkan sesi perdagangan baru, sehingga sesi terbaru tetap merupakan hari bursa sebelumnya.',

  'stock.back': '← Temukan saham',
  'stock.loading': 'Membuka ringkasan riset…',
  'stock.errorTitle': 'Saham ini tidak tersedia.',
  'stock.sectorMissing': 'Sektor tidak tersedia',
  'stock.overall': 'Keseluruhan',
  'stock.rank': 'Peringkat semesta {rank}',
  'stock.scores': 'Skor analisis',
  'stock.compare': 'Bandingkan',
  'stock.scoring':
    'Menghitung skor saham ini terhadap seluruh semesta…',
  'stock.scoreError': 'Skor metode tidak tersedia.',
  'stock.plain': 'Penjelasan sederhana',
  'stock.whyInteresting': 'Apa yang menonjol dari saham ini',
  'stock.noneInteresting':
    'Saat ini tidak ada sinyal atau tanda aktivitas tidak biasa yang terkait dengan saham ini di data tersimpan.',
  'stock.viewDetails': 'Lihat detail',
  'stock.why': 'Mengapa',
  'stock.tests': 'Tes',
  'stock.evidence': 'Bukti',
  'stock.missing': 'Data yang kurang: {fields}.',
  'stock.methodology': 'Metodologi',
  'stock.sourceLine': 'Sumber: {source}',
  'stock.version': 'versi {version}',
  'stock.notApplied': 'Tidak diterapkan',
  'stock.noScore': 'Tidak ada skor',
  'stock.whyUnusual': 'Mengapa ini tidak biasa?',
  'stock.flaggedFrom': 'Ditandai dari',
  'stock.deviations': '{count} simpangan baku',
  'stock.figures': 'Angka yang mendasari',
  'stock.figuresHelp':
    'Skor di atas dihitung dari input yang tersimpan ini.',
  'stock.marketCap': 'Kapitalisasi pasar',
  'stock.pe': 'P/E',
  'stock.pb': 'P/B',
  'stock.foreign': 'Arus masuk asing bersih',
  'stock.weights': 'Bobot yang digunakan:',
  'stock.quality': 'Kualitas',
  'stock.value': 'Nilai',
  'stock.momentum': 'Momentum',
  'stock.flow': 'Arus dana asing',
  'stock.pillars':
    'Skor keseluruhan adalah rata-rata tertimbang dari pilar yang tersedia. Pilar yang tidak memiliki data dikeluarkan, lalu bobot yang tersisa diskalakan ulang. Saham dengan kurang dari tiga pilar yang tersedia tidak diberi peringkat.',
  'stock.calculated': 'Dihitung dari Sectors + Yahoo Finance',
  'stock.howOverall': 'Bagaimana skor keseluruhan dihitung',
  'stock.chartTitle': 'Harga',
  'stock.momentumNote':
    'Riwayat harga Yahoo Finance digunakan ketika kartu momentum mencantumkan Yahoo Finance sebagai sumber.',

  'method.piotroski.title': 'Piotroski',
  'method.piotroski.beginner':
    'Checklist sembilan poin untuk melihat kondisi keuangan perusahaan: apakah perusahaan menghasilkan laba, apakah laba tersebut berubah menjadi arus kas, dan apakah neracanya membaik dibanding tahun sebelumnya? Skor menunjukkan berapa banyak tes yang terpenuhi. Ini memberikan cara terstruktur untuk melihat kekuatan keuangan, bukan hanya harga saham.',
  'method.piotroski.methodology':
    'Sembilan tes ya-atau-tidak dibandingkan dengan tahun buku sebelumnya. Skor adalah jumlah tes yang lolos. Sedikitnya enam tes harus dapat dihitung. Perusahaan keuangan dikecualikan dan menggunakan Financial Quality sebagai gantinya.',
  'method.piotroski.headline': 'Skor F {score} dari 9.',

  'method.magic_formula.title': 'Magic Formula',
  'method.magic_formula.beginner':
    'Kerangka yang melihat profitabilitas dan valuasi secara bersamaan. Metode ini melihat seberapa efisien perusahaan menghasilkan laba dari modal yang digunakan dan berapa banyak investor membayar untuk laba tersebut. Skor yang lebih tinggi berarti kedua ukuran tersebut memiliki peringkat yang lebih baik dibanding saham lain.',
  'method.magic_formula.methodology':
    'Earnings yield dan return on capital diperingkat lalu digabungkan menjadi persentil, dengan 100 sebagai peringkat tertinggi. Dalam cache ini, earnings yield adalah 1/P/E dan return on capital adalah ROE. Perusahaan keuangan dan utilitas dikecualikan. Pilar nilai kemudian memeringkat ulang hasil tersebut di antara saham sejenis jika jumlah pembanding mencukupi.',
  'method.magic_formula.headline':
    'Earnings yield {ey}, return on capital {roc}. Persentil {pct}.',

  'method.momentum.title': 'Momentum',
  'method.momentum.beginner':
    'Mengukur bagaimana harga saham bergerak dalam periode yang lebih panjang, sambil mengabaikan bulan terakhir. Skor menggunakan perubahan dari 12 bulan lalu hingga 1 bulan lalu, kemudian memeringkatnya terhadap saham Indonesia lainnya. Bulan terakhir dikeluarkan agar pergerakan harga yang sangat baru tidak terlalu mendominasi.',
  'method.momentum.methodology':
    'Momentum 12-1 adalah imbal hasil dari 12 bulan lalu hingga 1 bulan lalu, kemudian diperingkat sebagai persentil di seluruh semesta. Jika riwayat tersebut tidak tersedia, perubahan harga penutupan harian dalam snapshot digunakan sebagai fallback satu hari.',
  'method.momentum.twelve':
    'Imbal hasil 12-1 {ret}. Persentil {pct}.',
  'method.momentum.daily':
    'Diperingkat berdasarkan pergerakan harian dalam snapshot: {ret}. Persentil {pct}.',

  'method.foreign_flow.title': 'Arus Dana Asing',
  'method.foreign_flow.beginner':
    'Mengukur aktivitas beli atau jual investor asing dibandingkan dengan aktivitas perdagangan asing. Skor yang lebih tinggi menunjukkan pembelian bersih asing yang lebih kuat dibanding saham lain dalam semesta. Ini menambahkan konteks arus dana yang tidak terlihat dalam laporan keuangan standar.',
  'method.foreign_flow.methodology':
    'Pembelian bersih asing dibagi omzet asing, kemudian digabungkan dengan omzet saham tersebut relatif terhadap semesta dan diperingkat sebagai persentil. Ini adalah skor kekuatan dan terpisah dari Z-score aktivitas tidak biasa.',
  'method.foreign_flow.headline':
    'Arus asing bersih sebesar {ratio} dari omzet asing. Persentil {pct}.',

  'method.financials_quality.title': 'Kualitas Keuangan',
  'method.financials_quality.beginner':
    'Bank dan perusahaan keuangan lainnya dinilai menggunakan metrik yang lebih relevan dengan model bisnis mereka, terutama tingkat pengembalian yang dihasilkan dari ekuitas pemegang saham. Checklist perusahaan umum tidak digunakan untuk bisnis ini, sehingga metode ini menggantikannya.',
  'method.financials_quality.methodology':
    'Digunakan hanya untuk bank dan perusahaan keuangan lainnya. Metrik yang tersedia diperingkat sebagai persentil di dalam kelompok keuangan. Net interest margin dan non-performing loans sering tidak tersedia dalam cache ini, sehingga ROE bisa menjadi satu-satunya input yang tersedia.',
  'method.none': 'Metode ini tidak menghasilkan data.',
  'method.notApplied': 'Metode ini tidak diterapkan pada saham ini.',
  'method.noScore': 'Data tidak cukup untuk menghitung skor.',
  'method.fallback': 'Skor dari semesta yang tersimpan.',

  'piotroski.roa_positive': 'ROA > 0',
  'piotroski.cfo_positive': 'Arus kas operasi > 0',
  'piotroski.roa_increased': 'ROA lebih tinggi dari tahun sebelumnya',
  'piotroski.accrual': 'Arus kas operasi > laba bersih',
  'piotroski.leverage_decreased':
    'Rasio utang jangka panjang lebih rendah dari tahun sebelumnya',
  'piotroski.current_ratio_increased':
    'Rasio lancar lebih tinggi dari tahun sebelumnya',
  'piotroski.no_new_shares': 'Tidak ada penerbitan saham baru',
  'piotroski.gross_margin_increased':
    'Marjin kotor lebih tinggi dari tahun sebelumnya',
  'piotroski.asset_turnover_increased':
    'Perputaran aset lebih tinggi dari tahun sebelumnya',
  'piotroski.pass': 'lolos',
  'piotroski.fail': 'tidak lolos',
  'piotroski.unknown': 'data tidak cukup',

  'signal.mover.method':
    'Ditandai ketika perubahan absolut harga penutupan harian mencapai sedikitnya 5%. Perubahan ini berasal dari snapshot semesta Sectors.',
  'signal.fifty_two_week_high.method':
    'Ditandai dari label tertinggi 52 minggu Sectors, atau ketika harga penutupan berada dalam 2% dari harga tertinggi 52 minggu pada overlay harga Yahoo Finance.',
  'signal.foreign_accumulation.method':
    'Ditandai ketika arus masuk asing bersih sedikitnya Rp 1 miliar dan sedikitnya 15% dari omzet asing pada hari arus asing Sectors terbaru yang tersimpan.',
  'signal.insider_buying.method':
    'Ditandai dari laporan pembelian orang dalam yang disediakan Sectors dalam jendela laporan yang tersimpan.',

  'anomaly.volume.high': 'Lonjakan volume',
  'anomaly.volume.low': 'Volume sangat rendah',
  'anomaly.flow.high': 'Lonjakan arus masuk asing',
  'anomaly.flow.low': 'Lonjakan arus keluar asing',
  'anomaly.volume.referenceHigh':
    'Volume perdagangan pada sesi ini jauh lebih tinggi dibanding riwayat saham tersebut sendiri.',
  'anomaly.volume.referenceLow':
    'Volume perdagangan pada sesi ini jauh lebih rendah dibanding riwayat saham tersebut sendiri.',
  'anomaly.flow.referenceHigh':
    'Pembelian asing pada saham ini jauh lebih kuat dibanding saham lain pada hari yang sama.',
  'anomaly.flow.referenceLow':
    'Penjualan asing pada saham ini jauh lebih kuat dibanding saham lain pada hari yang sama.',
  'anomaly.volume.method':
    'Standard score sesi tersimpan terbaru dibandingkan dengan baseline volume historis saham tersebut. Sesi terbaru tidak dimasukkan ke dalam baseline. Yahoo Finance menyediakan data volume historis.',
  'anomaly.flow.method':
    'Robust standard score dari arus masuk asing bersih dibagi nilai transaksi rata-rata saham, diukur di antara saham pada hari yang sama. Sectors menyediakan data arus asing; Yahoo Finance menyediakan input nilai transaksi.',
  'anomaly.volume.reason':
    'Volume {observed} berada {z} simpangan baku {direction} rata-rata historis saham ini sebesar {baseline}.',
  'anomaly.flow.reason':
    'Arus asing pada hari ini sebesar {multiple}× nilai transaksi biasanya dan berada {z} simpangan baku {direction} median pasar.',
  'anomaly.above': 'di atas',
  'anomaly.below': 'di bawah',
  'anomaly.z': 'Z-score',

  'unusual.kicker': 'Temuan pasar',
  'unusual.title': 'Apa yang tidak biasa di pasar?',
  'unusual.intro':
    'Volume dibandingkan dengan riwayat masing-masing saham. Arus dana asing dibandingkan dengan saham lain pada hari yang sama.',
  'unusual.sector': 'Sektor',
  'unusual.subsector': 'Subsektor',
  'unusual.kind': 'Aktivitas tidak biasa',
  'unusual.all': 'Semua',
  'unusual.volume': 'Volume',
  'unusual.flow': 'Arus dana asing',
  'unusual.loading': 'Mencari aktivitas tidak biasa…',
  'unusual.errorTitle':
    'Aktivitas tidak biasa tidak dapat dimuat.',
  'unusual.emptyTitle':
    'Tidak ada aktivitas tidak biasa yang cocok dengan filter ini.',
  'unusual.emptyDetail':
    'Coba semua sektor, atau beralih antara volume dan arus dana asing.',
  'unusual.count': '{count} tanda aktivitas tidak biasa',
  'unusual.in': 'di {name}',
  'unusual.spanLabel': 'Per',
  'unusual.spanHelp':
    'Setiap kartu diberi tanggal sesuai sesi perdagangan yang diukur. Jika sesinya berbeda, rentang tanggal di atas mencakup semua kartu dalam daftar.',
  'unusual.why': 'Mengapa ini tidak biasa?',
  'unusual.latestVolume': 'Volume terbaru',
  'unusual.flowVsValue': 'Arus vs nilai transaksi',
  'unusual.ownAverage': 'Rata-rata historis sendiri',
  'unusual.sameDayMedian': 'Median hari yang sama',
  'unusual.flaggedFrom': 'Ditandai dari',
  'unusual.method': 'Metodologi',
  'unusual.showMore': 'Tampilkan lagi',
  'unusual.how': 'Bagaimana aktivitas tidak biasa diukur',
  'unusual.noteVolume':
    'Volume menggunakan sesi Yahoo Finance terbaru untuk saham tersebut dan membandingkannya dengan sesi-sesi sebelumnya. Tanggal pada kartu adalah sesi yang diukur.',
  'unusual.noteFlow':
    'Arus dana asing menggunakan hari perdagangan Sectors yang tersimpan dan membandingkan saham tersebut dengan saham lain pada hari yang sama. Tanggal pada kartu adalah hari yang diukur.',

  'compare.kicker': 'Perbandingan',
  'compare.title': 'Bandingkan dua atau tiga saham.',
  'compare.intro':
    'Bandingkan skor, sinyal, dan karakteristik utama secara berdampingan. Buka kode saham untuk melihat bukti pendukungnya.',
  'compare.first': 'Pertama',
  'compare.second': 'Kedua',
  'compare.third': 'Ketiga, opsional',
  'compare.submit': 'Bandingkan',
  'compare.loading': 'Memuat ringkasan riset…',
  'compare.errorTitle':
    'Saham-saham tersebut tidak dapat dibandingkan.',
  'compare.idleTitle': 'Tambahkan setidaknya dua kode saham.',
  'compare.idleDetail':
    'Setiap kolom mempertahankan skor, sinyal, dan data yang tersedia untuk sahamnya sendiri.',
  'compare.overall': 'Keseluruhan',
  'compare.signals': 'Sinyal',
  'compare.anomaly': 'Aktivitas tidak biasa',
  'compare.footnote':
    'Dihitung dari Sectors, dengan riwayat harga Yahoo Finance ketika momentum suatu saham menggunakannya. Buka kode saham untuk melihat buktinya.',
  'compare.loaded': 'berhasil dimuat',
  'compare.unavailable': 'Tidak tersedia',

  'field.return_12m': 'Imbal hasil 12 bulan',
  'field.return_1m': 'Imbal hasil 1 bulan',
  'field.twelve_minus_one': 'Momentum 12-1',
  'field.daily_return': 'Imbal hasil harian',
  'field.source': 'Imbal hasil yang digunakan',
  'field.ranked_value': 'Nilai yang diperingkat',
  'field.earnings_yield': 'Earnings yield',
  'field.return_on_capital': 'Return on capital',
  'field.earnings_yield_rank': 'Peringkat earnings yield',
  'field.return_on_capital_rank': 'Peringkat return on capital',
  'field.combined_rank': 'Peringkat gabungan',
  'field.percentile': 'Persentil',
  'field.net_foreign_inflow': 'Arus masuk asing bersih',
  'field.foreign_turnover': 'Omzet asing',
  'field.net_ratio': 'Bersih / omzet asing',
  'field.relative_volume': 'Omzet vs median semesta',
  'field.return_on_equity': 'ROE',
  'field.net_interest_margin': 'Net interest margin',
  'field.non_performing_loans': 'Non-performing loans',
  'field.roe_percentile': 'Persentil ROE',
  'field.nim_percentile': 'Persentil NIM',
  'field.npl_percentile': 'Persentil NPL',
  'field.parts_used': 'Metrik yang digunakan',
  'field.tests_computable': 'Tes yang dapat dihitung',
  'field.tests_passed': 'Tes yang lolos',
  'field.f_score': 'Skor F',
  'source.twelve_minus_one':
    'Imbal hasil 12 bulan hingga 1 bulan yang lalu',
  'source.daily_return':
    'Perubahan harga harian dalam snapshot',
};

export type MessageKey = keyof typeof en;

export function text(
  current: Locale,
  key: MessageKey,
  vars?: Record<string, string | number>
): string {
  let value: string = current === 'id' ? id[key] : en[key];

  if (!vars) return value;

  for (const [name, replacement] of Object.entries(vars)) {
    value = value.replaceAll(`{${name}}`, String(replacement));
  }

  return value;
}
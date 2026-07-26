import React, { useState, useEffect, useRef } from 'react'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Legend, Filler } from 'chart.js'
import { Line, Bar, Pie, Doughnut } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Legend, Filler)

function isDarkMode() {
  return document.documentElement.getAttribute('data-theme') === 'dark'
}

function nepaliNumber(value) {
  if (value === null || value === undefined) return '0'
  const num = Number(value)
  if (isNaN(num)) return String(value)
  const negative = num < 0
  const abs = Math.abs(num)
  if (abs % 1 !== 0) {
    const parts = abs.toFixed(2).split('.')
    let intStr = parts[0]
    let result = intStr.slice(-3)
    let rem = intStr.slice(0, -3)
    while (rem) { result = rem.slice(-2) + ',' + result; rem = rem.slice(0, -2) }
    return (negative ? '-' : '') + result + '.' + parts[1]
  }
  const intStr = String(abs)
  if (intStr.length <= 3) return (negative ? '-' : '') + intStr
  let result = intStr.slice(-3)
  let rem = intStr.slice(0, -3)
  while (rem) { result = rem.slice(-2) + ',' + result; rem = rem.slice(0, -2) }
  return (negative ? '-' : '') + result
}

function nepaliCurrency(value) {
  return '\u0930\u0942 ' + nepaliNumber(value)
}

function chartColors() {
  const dark = isDarkMode()
  return {
    text: dark ? '#ffffff' : '#000000',
    grid: dark ? 'rgba(255,255,255,0.1)' : '#f1f5f9',
    tooltipBg: dark ? '#1e293b' : '#ffffff',
    tooltipTitle: dark ? '#ffffff' : '#000000',
    tooltipBody: dark ? '#e2e8f0' : '#1e293b',
  }
}

function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
  return ''
}

async function apiGet(url) {
  const res = await fetch(url, { credentials: 'include', headers: { 'X-CSRFToken': getCookie('csrftoken') } })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

function AnimatedCounter({ value, prefix = '', suffix = '', duration = 1200 }) {
  const [display, setDisplay] = useState(0)
  const ref = useRef(null)
  useEffect(() => {
    const target = parseFloat(value) || 0
    const start = display
    const startTime = Date.now()
    const tick = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(Math.round(start + (target - start) * eased))
      if (progress < 1) ref.current = requestAnimationFrame(tick)
    }
    ref.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(ref.current)
  }, [value])
  return <span>{prefix}{nepaliNumber(display)}{suffix}</span>
}

function KPICard({ icon, colorClass, label, value, prefix = '', suffix = '', delay = 0 }) {
  const [visible, setVisible] = useState(false)
  useEffect(() => { const t = setTimeout(() => setVisible(true), delay); return () => clearTimeout(t) }, [])
  return (
    <div className="kpi-card" style={{
      opacity: visible ? 1 : 0, transform: visible ? 'translateY(0)' : 'translateY(20px)',
      transition: 'all 0.5s cubic-bezier(0.4,0,0.2,1)',
      borderLeft: 'none',
      borderTop: `4px solid var(--${colorClass === 'blue' ? 'primary' : colorClass === 'green' ? 'success' : colorClass === 'yellow' ? 'warning' : colorClass === 'red' ? 'danger' : colorClass === 'purple' ? 'secondary' : 'info'})`
    }}>
      <div className={`kpi-icon ${colorClass}`}>{icon}</div>
      <div className="kpi-info">
        <div className="kpi-label">{label}</div>
        <div className="kpi-value"><AnimatedCounter value={value} prefix={prefix} suffix={suffix} /></div>
      </div>
    </div>
  )
}

function Toast({ message, type = 'success', onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 4000); return () => clearTimeout(t) }, [])
  return (
    <div className={`alert alert-${type}`} style={{ position: 'fixed', top: 20, right: 20, zIndex: 999, animation: 'slideInRight 0.3s ease' }}>
      {message}
      <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', marginLeft: 12, fontSize: 18 }}>&times;</button>
    </div>
  )
}

function statusBadge(status) {
  const m = { Completed: 'badge-success', Draft: 'badge-warning', Returned: 'badge-danger', Void: 'badge-danger' }
  return `badge ${m[status] || 'badge-info'}`
}

const CHART_COLORS = ['#2563eb','#7c3aed','#059669','#d97706','#dc2626','#0891b2','#f59e0b','#06b6d4','#8b5cf6','#ec4899']

export default function DashboardApp() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)
  const [days, setDays] = useState(30)
  const [, forceRender] = useState(0)

  useEffect(() => {
    const handler = () => forceRender(x => x + 1)
    window.addEventListener('themechange', handler)
    return () => window.removeEventListener('themechange', handler)
  }, [])

  useEffect(() => { loadData() }, [days])

  async function loadData() {
    setLoading(true)
    try {
      const json = await apiGet(`/api/dashboard/?days=${days}`)
      setData(json)
    } catch (e) {
      setToast(`Error: ${e.message}`)
    }
    setLoading(false)
  }

  const cc = chartColors()

  const d = data || {}
  const stockValue = d.total_stock_value || 0
  const lowStock = d.low_stock_count || 0
  const pendingPOs = d.pending_pos || 0
  const sales30d = d.recent_sales || 0
  const salesCount = d.recent_sales_count || 0
  const productCount = d.product_count || 0
  const customerCount = d.customer_count || 0
  const supplierCount = d.supplier_count || 0
  const alertCount = d.unresolved_alerts || 0
  const purchaseCost = d.purchase_cost || 0
  const prevSales = d.previous_sales || 0
  const salesGrowth = prevSales > 0 ? ((sales30d - prevSales) / prevSales * 100) : 0

  const topProducts = (d.top_products || []).slice(0, 5)
  const recentTx = (d.recent_transactions || []).slice(0, 10)

  const sortedCats = (d.stock_by_category || [])
    .map(c => ({ label: c['product__category__name'] || 'Unknown', value: parseFloat(c.total), productCount: c.product_count || 0, totalUnits: c.total_units || 0, avgPrice: parseFloat(c.avg_price) || 0 }))
    .sort((a, b) => b.value - a.value)

  const catLabels = sortedCats.map(c => c.label)
  const catValues = sortedCats.map(c => c.value)
  const maxIdx = catValues.indexOf(Math.max(...catValues))
  const explodedOffsets = catValues.map((_, i) => i === maxIdx ? 15 : 0)
  const totalStockVal = stockValue

  const movements = d.stock_movements || {}
  const movementKeys = ['SALE','PURCHASE','ADJUSTMENT','TRANSFER','RETURN']
  const movementLabels = ['Sales','Purchases','Adjustments','Transfers','Returns']
  const movementColors = ['#dc2626','#059669','#d97706','#6366f1','#7c3aed']
  const movementData = movementKeys.map(k => movements[k] || movements[k+'_OUT'] || 0)
  const movementTotal = movementData.reduce((a, b) => a + b, 0)

  const trend = (d.sales_trend || []).length > 0
    ? { labels: d.sales_trend.map(x => { const p = x.date?.split('-'); return p ? `${p[2]}/${p[1]}` : x.date }), values: d.sales_trend.map(x => parseFloat(x.total) || 0) }
    : { labels: [], values: [] }

  const salesCat = (d.sales_by_category || [])
    .map(c => ({ label: c['product__category__name'] || 'Unknown', revenue: parseFloat(c.total_revenue) || 0, units: c.total_quantity || 0 }))
    .sort((a, b) => b.revenue - a.revenue)
  const salesCatLabels = salesCat.map(c => c.label)
  const salesCatValues = salesCat.map(c => c.revenue)
  const salesCatTotal = salesCatValues.reduce((a, b) => a + b, 0)

  const topCust = (d.top_customers || []).map(c => ({ name: c['customer__name'] || 'Unknown', spent: parseFloat(c.total_spent) || 0, txns: c.transaction_count || 0 }))
  const custLabels = topCust.map(c => c.name)
  const custValues = topCust.map(c => c.spent)

  const health = d.stock_health || { out_of_stock: 0, low_stock: 0, healthy: 0 }
  const healthTotal = health.out_of_stock + health.low_stock + health.healthy

  const profitCats = (d.profit_by_category || []).map(c => ({
    name: c['product__category__name'] || 'Unknown',
    revenue: parseFloat(c.revenue) || 0,
    cost: parseFloat(c.cost) || 0,
  })).sort((a, b) => (b.revenue - b.cost) - (a.revenue - a.cost))

  const purchTrend = (d.purchase_trend || []).map(x => {
    const p = x.date?.split('-'); return { date: p ? `${p[2]}/${p[1]}` : x.date, total: parseFloat(x.total) || 0 }
  })
  const purchTrendMap = {}
  purchTrend.forEach(x => { purchTrendMap[x.date] = x.total })
  const flowLabels = trend.labels.length > 0 ? trend.labels : purchTrend.map(x => x.date)
  const flowSales = flowLabels.map(l => trend.values[trend.labels.indexOf(l)] || 0)
  const flowPurchases = flowLabels.map(l => purchTrendMap[l] || 0)

  if (loading) return (
    <div style={{ padding: 32 }}>
      <div className="kpi-grid">{[1,2,3,4,5,6,7,8].map(i => <div key={i} className="skeleton" style={{ height: 100, borderRadius: 12 }} />)}</div>
      <div className="skeleton" style={{ height: 380, borderRadius: 12, marginTop: 24 }} />
      <div className="skeleton" style={{ height: 300, borderRadius: 12, marginTop: 16 }} />
    </div>
  )

  const chartBodyStyle = { padding: '16px 20px 20px' }
  const chartMinH = { minHeight: 340 }

  return (
    <div>
      {toast && <Toast message={toast} onClose={() => setToast(null)} />}

      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select value={days} onChange={e => setDays(parseInt(e.target.value))}
            className="form-input" style={{ width: 130, padding: '8px 12px', fontSize: 13 }}>
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
            <option value={365}>1 year</option>
          </select>
          <button className="btn btn-outline btn-sm" onClick={() => { loadData(); setToast('Refreshed!') }}><i className="fa-solid fa-rotate-right"></i></button>
        </div>
      </div>

      <div className="kpi-grid">
        <KPICard icon={<i className="fa-solid fa-scale-balanced"></i>} colorClass="blue" label="Total Stock Value" value={stockValue} prefix="रू " delay={100} />
        <KPICard icon={<i className="fa-solid fa-triangle-exclamation"></i>} colorClass="red" label="Low Stock Items" value={lowStock} delay={200} />
        <KPICard icon={<i className="fa-solid fa-cart-shopping"></i>} colorClass="yellow" label="Pending POs" value={pendingPOs} delay={300} />
        <KPICard icon={<i className="fa-solid fa-money-bill-wave"></i>} colorClass="green" label={`Sales (${days}d)`} value={sales30d} prefix="रू " delay={400} />
        <KPICard icon={<i className="fa-solid fa-boxes-stacked"></i>} colorClass="purple" label="Products" value={productCount} delay={500} />
        <KPICard icon={<i className="fa-solid fa-users"></i>} colorClass="blue" label="Customers" value={customerCount} delay={600} />
        <KPICard icon={<i className="fa-solid fa-truck"></i>} colorClass="green" label="Suppliers" value={supplierCount} delay={700} />
        <KPICard
          icon={salesGrowth >= 0 ? <i className="fa-solid fa-arrow-up"></i> : <i className="fa-solid fa-arrow-down"></i>}
          colorClass={salesGrowth >= 0 ? 'green' : 'red'}
          label="Sales Growth"
          value={Math.abs(salesGrowth)}
          prefix={salesGrowth >= 0 ? '+': ''}
          suffix="%"
          delay={800} />
      </div>

      <div className="dashboard-grid-2fr-1fr" style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24, marginBottom: 32 }}>
        <div className="card">
          <div className="card-header">
            <h3 style={{ fontSize: 18, fontWeight: 700, textAlign: 'center' }}>Sales Trend</h3>
            <span className="badge badge-info">{salesCount} txns</span>
          </div>
          <div className="card-body" style={{ ...chartBodyStyle, ...chartMinH }}>
            {trend.labels.length > 0 ? (
              <Line data={{
                labels: trend.labels,
                datasets: [{ label: 'Sales (रू)', data: trend.values, borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,0.08)', fill: true, borderWidth: 2.5, pointBackgroundColor: '#2563eb' }]
              }} options={{
                responsive: true, maintainAspectRatio: false,
                plugins: {
                  legend: { display: false },
                  tooltip: { backgroundColor: cc.tooltipBg, titleColor: cc.tooltipTitle, bodyColor: cc.tooltipBody,
                    callbacks: {
                      label: ctx => {
                        const val = nepaliNumber(parseFloat(ctx.raw))
                        return [`  Sales: रू ${val}`, `  Date: ${ctx.label}`]
                      }
                    }
                  }
                },
                scales: { y: { beginAtZero: true, grid: { color: cc.grid }, ticks: { color: cc.text, callback: v => `रू ${nepaliNumber(v)}` } }, x: { grid: { display: false }, ticks: { color: cc.text } } },
                elements: { line: { tension: 0.4 }, point: { radius: 4, hoverRadius: 6 } },
                animation: { duration: 1500, easing: 'easeOutQuart' }
              }} />
            ) : <div style={{ textAlign: 'center', padding: 80, color: 'var(--text-muted)' }}>No sales data for this period</div>}
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h3 style={{ fontSize: 18, fontWeight: 700, textAlign: 'center' }}>Stock by Category</h3></div>
          <div className="card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', ...chartMinH }}>
            {catLabels.length > 0 ? (
              <Pie data={{
                labels: catLabels,
                datasets: [{
                  data: catValues,
                  backgroundColor: CHART_COLORS,
                  borderWidth: 2,
                  borderColor: '#fff',
                  offset: explodedOffsets,
                }]
              }} options={{
                responsive: true, maintainAspectRatio: false,
                plugins: {
                  legend: { position: 'bottom', labels: { color: cc.text, padding: 14, usePointStyle: true, font: { size: 11 } } },
                  tooltip: { backgroundColor: cc.tooltipBg, titleColor: cc.tooltipTitle, bodyColor: cc.tooltipBody,
                    callbacks: {
                      label: ctx => {
                        const c = sortedCats[ctx.dataIndex]
                        if (!c) return ctx.label
                        const pct = totalStockVal > 0 ? ((c.value / totalStockVal) * 100).toFixed(1) : 0
                        return [
                          `${ctx.label}`,
                          `  Total Value: रू ${nepaliNumber(c.value)}`,
                          `  Products: ${c.productCount}  |  Units: ${nepaliNumber(c.totalUnits)}`,
                          `  Avg Price: रू ${nepaliNumber(c.avgPrice)}`,
                          `  Share: ${pct}% of total stock`,
                        ]
                      }
                    }
                  }
                },
                animation: { animateRotate: true, duration: 1200 }
              }} />
            ) : <div style={{ textAlign: 'center', padding: 80, color: 'var(--text-muted)' }}>No category data</div>}
          </div>
        </div>
      </div>

      <div className="dashboard-grid-3" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 24, marginBottom: 32 }}>
        <div className="card">
          <div className="card-header"><h3 style={{ fontSize: 18, fontWeight: 700, textAlign: 'center' }}>Top Customers</h3></div>
          <div className="card-body" style={{ ...chartBodyStyle, ...chartMinH }}>
            {custLabels.length > 0 ? (
              <Bar data={{
                labels: custLabels,
                datasets: [{ data: custValues, backgroundColor: CHART_COLORS.slice(0, custLabels.length), borderRadius: 8, borderSkipped: false }]
              }} options={{
                responsive: true, maintainAspectRatio: false, indexAxis: 'y',
                plugins: {
                  legend: { display: false },
                  tooltip: { backgroundColor: cc.tooltipBg, titleColor: cc.tooltipTitle, bodyColor: cc.tooltipBody,
                    callbacks: {
                      label: ctx => {
                        const c = topCust[ctx.dataIndex]
                        const lines = [`  Total Spent: रू ${nepaliNumber(parseFloat(ctx.raw))}`]
                        if (c) lines.push(`  Transactions: ${c.txns}`)
                        return lines
                      }
                    }
                  }
                },
                scales: { y: { grid: { display: false }, ticks: { color: cc.text, font: { size: 10 } } }, x: { grid: { color: cc.grid }, ticks: { color: cc.text, callback: v => `रू ${nepaliNumber(v)}` } } },
                animation: { duration: 1200 }
              }} />
            ) : <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>No customer data</div>}
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h3 style={{ fontSize: 18, fontWeight: 700, textAlign: 'center' }}>Sales by Category</h3></div>
          <div className="card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', ...chartMinH }}>
            {salesCatLabels.length > 0 ? (
              <Pie data={{
                labels: salesCatLabels,
                datasets: [{ data: salesCatValues, backgroundColor: CHART_COLORS, borderWidth: 2, borderColor: '#fff' }]
              }} options={{
                responsive: true, maintainAspectRatio: false,
                plugins: {
                  legend: { position: 'bottom', labels: { color: cc.text, padding: 10, usePointStyle: true, font: { size: 10 } } },
                  tooltip: { backgroundColor: cc.tooltipBg, titleColor: cc.tooltipTitle, bodyColor: cc.tooltipBody,
                    callbacks: {
                      label: ctx => {
                        const c = salesCat[ctx.dataIndex]
                        const pct = salesCatTotal > 0 ? ((parseFloat(ctx.raw) / salesCatTotal) * 100).toFixed(1) : 0
                        const lines = [`${ctx.label}`]
                        lines.push(`  Revenue: रू ${nepaliNumber(parseFloat(ctx.raw))}`)
                        if (c) lines.push(`  Units Sold: ${nepaliNumber(c.units)}`)
                        lines.push(`  Share: ${pct}% of total`)
                        return lines
                      }
                    }
                  }
                },
                animation: { animateRotate: true, duration: 1200 }
              }} />
            ) : <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>No sales data</div>}
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h3 style={{ fontSize: 18, fontWeight: 700, textAlign: 'center' }}>Stock Movement</h3></div>
          <div className="card-body" style={{ ...chartBodyStyle, ...chartMinH }}>
            {movementData.some(v => v > 0) ? (
              <Bar data={{
                labels: movementLabels,
                datasets: [{ data: movementData, backgroundColor: movementColors, borderRadius: 8, borderSkipped: false }]
              }} options={{
                responsive: true, maintainAspectRatio: false,
                plugins: {
                  legend: { display: false },
                  tooltip: { backgroundColor: cc.tooltipBg, titleColor: cc.tooltipTitle, bodyColor: cc.tooltipBody,
                    callbacks: {
                      label: ctx => {
                        const pct = movementTotal > 0 ? ((parseFloat(ctx.raw) / movementTotal) * 100).toFixed(1) : 0
                        return [`  ${ctx.label}: ${ctx.raw} movements`, `  Share: ${pct}% of total`]
                      }
                    }
                  }
                },
                scales: { y: { beginAtZero: true, grid: { color: cc.grid }, ticks: { color: cc.text } }, x: { grid: { display: false }, ticks: { color: cc.text } } },
                animation: { duration: 1200 }
              }} />
            ) : <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>No movement data</div>}
          </div>
        </div>
      </div>

      <div className="dashboard-grid-2fr-1fr" style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24, marginBottom: 32 }}>
        <div className="card">
          <div className="card-header"><h3 style={{ fontSize: 18, fontWeight: 700, textAlign: 'center' }}>Cash Flow</h3></div>
          <div className="card-body" style={{ ...chartBodyStyle, ...chartMinH }}>
            {flowLabels.length > 0 ? (
              <Line data={{
                labels: flowLabels,
                datasets: [
                  { label: 'Sales (रू)', data: flowSales, borderColor: '#059669', backgroundColor: 'rgba(5,150,105,0.08)', fill: true, borderWidth: 2.5, pointBackgroundColor: '#059669' },
                  { label: 'Purchases (रू)', data: flowPurchases, borderColor: '#dc2626', backgroundColor: 'rgba(220,38,38,0.08)', fill: true, borderWidth: 2.5, pointBackgroundColor: '#dc2626', borderDash: [5,5] },
                ]
              }} options={{
                responsive: true, maintainAspectRatio: false,
                plugins: {
                  legend: { position: 'top', labels: { color: cc.text, usePointStyle: true, font: { size: 11 } } },
                  tooltip: { backgroundColor: cc.tooltipBg, titleColor: cc.tooltipTitle, bodyColor: cc.tooltipBody,
                    callbacks: {
                      label: ctx => {
                        const val = nepaliNumber(parseFloat(ctx.raw))
                        return `  ${ctx.dataset.label}: रू ${val}`
                      }
                    }
                  }
                },
                scales: { y: { beginAtZero: true, grid: { color: cc.grid }, ticks: { color: cc.text, callback: v => `रू ${nepaliNumber(v)}` } }, x: { grid: { display: false }, ticks: { color: cc.text } } },
                elements: { line: { tension: 0.4 }, point: { radius: 3, hoverRadius: 5 } },
                animation: { duration: 1500, easing: 'easeOutQuart' }
              }} />
            ) : <div style={{ textAlign: 'center', padding: 80, color: 'var(--text-muted)' }}>Insufficient data for cash flow chart</div>}
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h3 style={{ fontSize: 18, fontWeight: 700, textAlign: 'center' }}>Stock Health</h3></div>
          <div className="card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', ...chartMinH }}>
            {healthTotal > 0 ? (
              <Doughnut data={{
                labels: ['Out of Stock', 'Low Stock', 'Healthy'],
                datasets: [{
                  data: [health.out_of_stock, health.low_stock, health.healthy],
                  backgroundColor: ['#dc2626', '#f59e0b', '#059669'],
                  borderWidth: 2,
                  borderColor: '#fff',
                }]
              }} options={{
                responsive: true, maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                  legend: { position: 'bottom', labels: { color: cc.text, padding: 12, usePointStyle: true, font: { size: 11 } } },
                  tooltip: { backgroundColor: cc.tooltipBg, titleColor: cc.tooltipTitle, bodyColor: cc.tooltipBody,
                    callbacks: {
                      label: ctx => {
                        const pct = ((ctx.raw / healthTotal) * 100).toFixed(1)
                        return [`  ${ctx.label}: ${ctx.raw} items`, `  Share: ${pct}% of total`]
                      }
                    }
                  }
                },
                animation: { animateRotate: true, duration: 1200 }
              }} />
            ) : <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>No stock data</div>}
          </div>
        </div>
      </div>

      <div className="dashboard-grid-2" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        <div className="card">
          <div className="card-header"><h3 style={{ fontSize: 18, fontWeight: 700, textAlign: 'center' }}>Top Products</h3></div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-scroll">
            <table>
              <thead><tr><th>Product</th><th>Sold</th><th>Revenue</th></tr></thead>
              <tbody>
                {topProducts.length > 0 ? topProducts.map((p, i) => (
                  <tr key={i} style={{ animation: `fadeInUp 0.3s ease ${i * 0.05}s backwards` }}>
                    <td style={{ fontWeight: 600, fontSize: 13 }}>{p.product__name}</td>
                    <td><span className={`badge ${p.total_qty > 20 ? 'badge-success' : p.total_qty > 5 ? 'badge-warning' : 'badge-danger'}`}>{p.total_qty}</span></td>
                    <td style={{ fontWeight: 600, fontSize: 13 }}>रू {nepaliNumber(parseFloat(p.total_revenue))}</td>
                  </tr>
                )) : <tr><td colSpan="3" style={{ textAlign: 'center', padding: 30, color: 'var(--text-muted)' }}>No sales yet</td></tr>}
              </tbody>
            </table>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h3 style={{ fontSize: 18, fontWeight: 700, textAlign: 'center' }}>Profit by Category</h3></div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-scroll">
            <table>
              <thead><tr><th>Category</th><th>Revenue</th><th>Cost</th><th>Profit</th><th>Margin</th></tr></thead>
              <tbody>
                {profitCats.length > 0 ? profitCats.map((c, i) => {
                  const profit = c.revenue - c.cost
                  const margin = c.revenue > 0 ? ((profit / c.revenue) * 100).toFixed(1) : 0
                  return (
                    <tr key={i} style={{ animation: `fadeInUp 0.3s ease ${i * 0.05}s backwards` }}>
                      <td style={{ fontWeight: 600, fontSize: 13 }}>{c.name}</td>
                      <td style={{ fontSize: 13 }}>रू {nepaliNumber(c.revenue)}</td>
                      <td style={{ fontSize: 13 }}>रू {nepaliNumber(c.cost)}</td>
                      <td style={{ fontWeight: 600, fontSize: 13, color: profit >= 0 ? 'var(--success)' : 'var(--danger)' }}>रू {nepaliNumber(Math.abs(profit))}</td>
                      <td><span className={`badge ${margin >= 50 ? 'badge-success' : margin >= 25 ? 'badge-warning' : 'badge-danger'}`}>{margin}%</span></td>
                    </tr>
                  )
                }) : <tr><td colSpan="5" style={{ textAlign: 'center', padding: 30, color: 'var(--text-muted)' }}>No profit data</td></tr>}
              </tbody>
            </table>
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 32 }}>
        <div className="card-header">
          <h3 style={{ fontSize: 18, fontWeight: 700, textAlign: 'center' }}>Recent Activity</h3>
          <a href="/sales/" className="btn btn-outline btn-sm">View All</a>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-scroll">
          <table>
            <thead><tr><th>Invoice</th><th>Customer</th><th>Amount</th><th>Status</th><th>Date</th></tr></thead>
            <tbody>
              {recentTx.length > 0 ? recentTx.map((t, i) => (
                <tr key={i} style={{ animation: `fadeInUp 0.3s ease ${i * 0.05}s backwards` }}>
                  <td style={{ fontWeight: 600, fontSize: 13 }}>{t.invoice_number || `#${t.id}`}</td>
                  <td style={{ fontSize: 13 }}>{t.customer__name || 'Walk-in'}</td>
                  <td style={{ fontWeight: 600, fontSize: 13 }}>रू {nepaliNumber(parseFloat(t.grand_total || 0))}</td>
                  <td><span className={statusBadge(t.status)}>{t.status}</span></td>
                  <td className="text-sm text-muted">{t.completed_at ? new Date(t.completed_at).toLocaleDateString() : '-'}</td>
                </tr>
              )) : <tr><td colSpan="5" style={{ textAlign: 'center', padding: 30, color: 'var(--text-muted)' }}>No transactions yet</td></tr>}
            </tbody>
          </table>
          </div>
        </div>
      </div>
    </div>
  )
}

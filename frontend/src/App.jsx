import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [fabrics, setFabrics] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('all')
  const [stats, setStats] = useState(null)
  const [scraping, setScraping] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [scrapeUrl, setScrapeUrl] = useState('')
  const [batchUrls, setBatchUrls] = useState('')
  const [galleryImages, setGalleryImages] = useState([])
  const [galleryIndex, setGalleryIndex] = useState(0)
  const [showGallery, setShowGallery] = useState(false)

  useEffect(() => {
    fetchFabrics()
    fetchStats()
  }, [activeTab])

  const fetchFabrics = async () => {
    try {
      setLoading(true)
      const rating = activeTab === 'all' ? null : activeTab
      const response = await axios.get(`${API_BASE_URL}/api/fabrics`, {
        params: { rating, limit: 1000 }
      })
      setFabrics(response.data)
      setError(null)
    } catch (err) {
      setError(`Failed to fetch fabrics: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/fabrics/stats`)
      setStats(response.data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  const updateRating = async (fabricId, rating) => {
    try {
      await axios.patch(`${API_BASE_URL}/api/fabrics/${fabricId}/rating`, { rating })
      await fetchFabrics()
      await fetchStats()
    } catch (err) {
      setError(`Failed to update rating: ${err.message}`)
    }
  }

  const handleScrape = async () => {
    if (!scrapeUrl.trim()) {
      setError('Please enter a URL')
      return
    }

    try {
      setScraping(true)
      setError(null)
      setSuccess(null)
      const response = await axios.post(`${API_BASE_URL}/api/fabrics/scrape`, {
        url: scrapeUrl.trim(),
      })
      setSuccess(`Successfully scraped: ${response.data.name}`)
      setScrapeUrl('')
      await fetchFabrics()
      await fetchStats()
    } catch (err) {
      setError(`Failed to scrape: ${err.response?.data?.detail || err.message}`)
    } finally {
      setScraping(false)
    }
  }

  const handleBatchScrape = async () => {
    if (!batchUrls.trim()) {
      setError('Please enter URLs (one per line)')
      return
    }

    const urls = batchUrls
      .split('\n')
      .map((u) => u.trim())
      .filter((u) => u && u.startsWith('http'))

    if (urls.length === 0) {
      setError('No valid URLs found')
      return
    }

    try {
      setScraping(true)
      setError(null)
      setSuccess(null)
      const response = await axios.post(`${API_BASE_URL}/api/fabrics/scrape-batch`, urls)
      setSuccess(
        `Batch scraping complete: ${response.data.results.length} succeeded, ${response.data.errors.length} errors`
      )
      setBatchUrls('')
      await fetchFabrics()
      await fetchStats()
    } catch (err) {
      setError(`Failed to batch scrape: ${err.response?.data?.detail || err.message}`)
    } finally {
      setScraping(false)
    }
  }

  const formatPrice = (price, currency = 'USD') => {
    if (!price) return 'Price not available'
    const symbol = {
      USD: '$',
      GBP: '£',
      EUR: '€',
    }[currency] || currency
    return `${symbol}${price.toFixed(2)}`
  }

  const getImageUrl = (imagePath) => {
    /**
     * Construct full URL for fabric image.
     * Images are stored in backend/static/images/ and served via /static/images/ endpoint.
     */
    if (!imagePath) return null
    if (imagePath.startsWith('http')) return imagePath  // External URL
    // Construct URL: http://localhost:8000/static/images/fabric_name_hash.jpg
    return `${API_BASE_URL}/${imagePath}`
  }

  const getAllImageUrls = (fabric) => {
    // Get all image URLs from fabric (image_paths array or fallback to image_path)
    const imagePaths = fabric.image_paths || (fabric.image_path ? [fabric.image_path] : [])
    return imagePaths.map(path => getImageUrl(path)).filter(url => url !== null)
  }

  const openGallery = (fabric, imageIndex = 0) => {
    const images = getAllImageUrls(fabric)
    if (images.length > 0) {
      setGalleryImages(images)
      setGalleryIndex(imageIndex)
      setShowGallery(true)
    }
  }

  const closeGallery = () => {
    setShowGallery(false)
    setGalleryImages([])
    setGalleryIndex(0)
  }

  const nextImage = () => {
    setGalleryIndex((prev) => (prev + 1) % galleryImages.length)
  }

  const prevImage = () => {
    setGalleryIndex((prev) => (prev - 1 + galleryImages.length) % galleryImages.length)
  }

  // Keyboard navigation for gallery
  useEffect(() => {
    const handleKeyPress = (e) => {
      if (!showGallery) return
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        setGalleryIndex((prev) => (prev - 1 + galleryImages.length) % galleryImages.length)
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        setGalleryIndex((prev) => (prev + 1) % galleryImages.length)
      } else if (e.key === 'Escape') {
        closeGallery()
      }
    }
    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [showGallery, galleryImages.length])

  return (
    <div className="container">
      <div className="header">
        <h1>Fabric Catalog</h1>
        <p>Browse and manage your fabric collection</p>
      </div>

      {/* Rating Tabs */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => setActiveTab('all')}
        >
          All {stats && `(${stats.total})`}
        </button>
        <button
          className={`tab ${activeTab === 'yes' ? 'active' : ''}`}
          onClick={() => setActiveTab('yes')}
        >
          Yes {stats && `(${stats.ratings.yes})`}
        </button>
        <button
          className={`tab ${activeTab === 'maybe' ? 'active' : ''}`}
          onClick={() => setActiveTab('maybe')}
        >
          Maybe {stats && `(${stats.ratings.maybe})`}
        </button>
        <button
          className={`tab ${activeTab === 'no' ? 'active' : ''}`}
          onClick={() => setActiveTab('no')}
        >
          No {stats && `(${stats.ratings.no})`}
        </button>
      </div>

      <div className="controls">
        <h2 style={{ marginBottom: '1rem' }}>Add Fabrics</h2>

        {error && <div className="error">{error}</div>}
        {success && <div className="success">{success}</div>}

        <div className="form-group">
          <label htmlFor="scrape-url">Single URL</label>
          <input
            id="scrape-url"
            type="text"
            placeholder="https://example.com/fabric"
            value={scrapeUrl}
            onChange={(e) => setScrapeUrl(e.target.value)}
            disabled={scraping}
          />
        </div>
        <button
          className="button"
          onClick={handleScrape}
          disabled={scraping}
        >
          {scraping ? 'Scraping...' : 'Scrape Fabric'}
        </button>

        <div style={{ marginTop: '2rem' }}>
          <div className="form-group">
            <label htmlFor="batch-urls">Batch URLs (one per line)</label>
            <textarea
              id="batch-urls"
              placeholder="https://example.com/fabric1&#10;https://example.com/fabric2"
              value={batchUrls}
              onChange={(e) => setBatchUrls(e.target.value)}
              disabled={scraping}
              style={{ minHeight: '100px', fontFamily: 'inherit' }}
            />
          </div>
          <button
            className="button"
            onClick={handleBatchScrape}
            disabled={scraping}
          >
            {scraping ? 'Scraping...' : 'Batch Scrape'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading fabrics...</div>
      ) : fabrics.length === 0 ? (
        <div className="empty-state">
          <h2>No fabrics found</h2>
          <p>Start by scraping a fabric URL above</p>
        </div>
      ) : (
        <div className="fabrics-grid">
          {fabrics.map((fabric) => (
            <div key={fabric.id} className="fabric-card">
              {/* Display fabric image if available */}
              {(() => {
                const imageUrls = getAllImageUrls(fabric)
                const firstImage = imageUrls[0]
                return firstImage ? (
                  <div style={{ position: 'relative', cursor: 'pointer' }} onClick={() => openGallery(fabric, 0)}>
                    <img
                      src={firstImage}
                      alt={fabric.name}
                      className="fabric-image"
                      onError={(e) => {
                        e.target.style.display = 'none'
                      }}
                      loading="lazy"
                    />
                    {imageUrls.length > 1 && (
                      <div className="image-count-badge">
                        {imageUrls.length} photos
                      </div>
                    )}
                  </div>
                ) : (
                  // Placeholder when no image is available
                  <div className="fabric-image" style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: '#f0f0f0',
                    color: '#999',
                    fontSize: '0.9rem'
                  }}>
                    No Image Available
                  </div>
                )
              })()}
              <div className="fabric-info">
                <h3 className="fabric-name">{fabric.name}</h3>
                {fabric.origin && (
                  <span className="origin-badge">{fabric.origin}</span>
                )}
                <div className="fabric-price">
                  {formatPrice(fabric.price, fabric.currency)}
                </div>
                {fabric.composition && (
                  <div className="fabric-details">
                    <strong>Composition:</strong> {fabric.composition}
                  </div>
                )}
                {fabric.width && (
                  <div className="fabric-details">
                    <strong>Width:</strong> {fabric.width}
                  </div>
                )}
                {fabric.color && (
                  <div className="fabric-details">
                    <strong>Color:</strong> {fabric.color}
                  </div>
                )}
                {fabric.brand && (
                  <div className="fabric-details">
                    <strong>Brand:</strong> {fabric.brand}
                  </div>
                )}
                <div className="fabric-rating">
                  <button
                    className={`rating-btn yes ${fabric.rating === 'yes' ? 'active' : ''}`}
                    onClick={() => updateRating(fabric.id, 'yes')}
                    title="Like"
                  >
                    ✓ Yes
                  </button>
                  <button
                    className={`rating-btn maybe ${fabric.rating === 'maybe' ? 'active' : ''}`}
                    onClick={() => updateRating(fabric.id, 'maybe')}
                    title="Unsure"
                  >
                    ? Maybe
                  </button>
                  <button
                    className={`rating-btn no ${fabric.rating === 'no' ? 'active' : ''}`}
                    onClick={() => updateRating(fabric.id, 'no')}
                    title="Dislike"
                  >
                    ✗ No
                  </button>
                </div>
                <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid #eee' }}>
                  <a
                    href={fabric.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: 'block',
                      textAlign: 'center',
                      padding: '0.5rem',
                      background: '#f8f9fa',
                      color: '#667eea',
                      textDecoration: 'none',
                      borderRadius: '4px',
                    }}
                  >
                    View Original
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Image Gallery Modal */}
      {showGallery && galleryImages.length > 0 && (
        <div className="gallery-modal" onClick={closeGallery}>
          <div className="gallery-content" onClick={(e) => e.stopPropagation()}>
            <button className="gallery-close" onClick={closeGallery}>&times;</button>
            <button className="gallery-nav gallery-prev" onClick={prevImage}>&#8249;</button>
            <img
              src={galleryImages[galleryIndex]}
              alt={`Image ${galleryIndex + 1} of ${galleryImages.length}`}
              className="gallery-main-image"
            />
            <button className="gallery-nav gallery-next" onClick={nextImage}>&#8250;</button>
            <div className="gallery-info">
              <span className="gallery-counter">{galleryIndex + 1} / {galleryImages.length}</span>
              <div className="gallery-hint">Use ← → arrow keys to navigate, Esc to close</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App

'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Aperture,
  ArrowDownToLine,
  ArrowLeftRight,
  BadgeCheck,
  Ban,
  BarChart3,
  Bell,
  Blend,
  Boxes,
  Brush,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  CloudUpload,
  Contrast,
  Crop,
  Download,
  Expand,
  Eye,
  FileImage,
  FolderClock,
  GitBranch,
  ImagePlus,
  Layers3,
  Lightbulb,
  Menu,
  Minus,
  MoreHorizontal,
  Palette,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Redo2,
  RotateCcw,
  Search,
  Settings2,
  SlidersHorizontal,
  Sparkles,
  SunMedium,
  Timer,
  Trash2,
  Upload,
  WandSparkles,
  X,
  Zap,
} from 'lucide-react'
import { api, pollJob, type ImageInfo, type JobResponse, type ProcessingResult } from '@/lib/api'

// ── Types ────────────────────────────────────────────────────────────

type Tool = { name: string; description: string; icon: React.ElementType; color: string }

type HistoryEntry = {
  imageId: string
  imageUrl: string
  label: string
  width: number
  height: number
  format: string
  sizeBytes: number
  processingTimeMs?: number
}

type Toast = { id: number; type: 'success' | 'error' | 'info'; message: string }

// ── Constants ────────────────────────────────────────────────────────

const tools: Tool[] = [
  { name: 'AI Upscaler', description: '2×, 4× and 4K enhancement', icon: Zap, color: 'violet' },
  { name: 'Background Remover', description: 'Clean transparent cutouts', icon: Layers3, color: 'teal' },
  { name: 'Background Changer', description: 'New scenes, colors & styles', icon: Blend, color: 'peach' },
  { name: 'Image Sharpener', description: 'Bring back fine details', icon: Aperture, color: 'blue' },
  { name: 'Noise Reduction', description: 'Remove grain and artifacts', icon: Sparkles, color: 'pink' },
  { name: 'Face Enhancer', description: 'Natural portrait retouching', icon: WandSparkles, color: 'gold' },
  { name: 'Color Enhancer', description: 'Balance light and color', icon: Palette, color: 'orange' },
  { name: 'Batch Processing', description: 'Process multiple images', icon: Boxes, color: 'green' },
]

const navGroups = [
  { label: 'Workspace', items: [['Dashboard', BarChart3], ['Recent Projects', FolderClock], ['All Images', FileImage]] },
  { label: 'Enhance', items: [['AI Upscaler', Zap], ['Image Sharpener', Aperture], ['Denoise', Sparkles], ['Face Enhancer', WandSparkles], ['Color Enhancer', Palette]] },
  { label: 'Background', items: [['Remove Background', Layers3], ['Change Background', Blend], ['Transparent PNG', ImagePlus]] },
  { label: 'Editor', items: [['Crop & Resize', Crop], ['Adjustments', SlidersHorizontal], ['Batch Processing', Boxes]] },
] as const

const TOOL_NAV_MAP: Record<string, string> = {
  'AI Upscaler': 'AI Upscaler',
  'Background Remover': 'Remove Background',
  'Background Changer': 'Change Background',
  'Image Sharpener': 'Image Sharpener',
  'Noise Reduction': 'Denoise',
  'Face Enhancer': 'Face Enhancer',
  'Color Enhancer': 'Color Enhancer',
  'Batch Processing': 'Batch Processing',
}

// ── Shared Components ────────────────────────────────────────────────

function Brand() {
  return <div className="brand"><div className="brand-mark"><Sparkles /></div><span>AI Image Studio</span><span className="open-badge">OPEN SOURCE</span></div>
}

function Sidebar({ collapsed, active, onSelect }: { collapsed: boolean; active: string; onSelect: (name: string) => void }) {
  return <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
    <div className="mobile-brand"><Brand /></div>
    <div className="sidebar-scroll">
      {navGroups.map((group) => <section className="nav-group" key={group.label}><p className="nav-label">{group.label}</p>{group.items.map(([label, Icon]) => <button key={label} className={`nav-item ${active === label ? 'active' : ''}`} onClick={() => onSelect(label)} title={collapsed ? label : undefined}><Icon /><span>{label}</span>{label === 'Dashboard' && !collapsed && <span className="shortcut">⌘1</span>}</button>)}</section>)}
    </div>
    <div className="sidebar-bottom"><button className="nav-item"><CircleHelp /><span>Help center</span></button><div className="profile"><div className="avatar">JD</div><div><strong>Jordan Davis</strong><small>Free workspace</small></div><MoreHorizontal /></div></div>
  </aside>
}

function Topbar({ onToggle, collapsed, onExport, theme, onThemeToggle, canUndo, canRedo, onUndo, onRedo, backendOnline }: {
  onToggle: () => void; collapsed: boolean; onExport: () => void; theme: 'light' | 'dark'; onThemeToggle: () => void
  canUndo: boolean; canRedo: boolean; onUndo: () => void; onRedo: () => void; backendOnline: boolean
}) {
  return <header className="topbar"><div className="topbar-left"><button className="icon-button sidebar-toggle" onClick={onToggle} aria-label="Toggle sidebar">{collapsed ? <PanelLeftOpen /> : <PanelLeftClose />}</button><Brand /><span className={`status-badge ${backendOnline ? 'connected' : 'disconnected'}`}><span className="dot" />{backendOnline ? 'Backend online' : 'Backend offline'}</span></div><div className="topbar-actions"><div className="history"><button className={`icon-button ${!canUndo ? 'disabled' : ''}`} onClick={onUndo} aria-label="Undo"><RotateCcw /></button><button className={`icon-button ${!canRedo ? 'disabled' : ''}`} onClick={onRedo} aria-label="Redo"><Redo2 /></button></div><div className="topbar-separator" /><button className="icon-button theme-toggle" onClick={onThemeToggle} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`} title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>{theme === 'light' ? <SunMedium /> : <Lightbulb />}</button><button className="icon-button" aria-label="Settings"><Settings2 /></button><button className="icon-button github" aria-label="Open GitHub"><GitBranch /></button><button className="export-button" onClick={onExport}><ArrowDownToLine /> Export</button></div></header>
}

function UploadCard({ onFile }: { onFile: (file: File) => void }) {
  const ref = useRef<HTMLInputElement>(null)
  const handle = (file?: File) => { if (file && file.type.startsWith('image/')) onFile(file) }
  return <div className="upload-card" onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); handle(e.dataTransfer.files[0]) }}>
    <input ref={ref} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(e) => handle(e.target.files?.[0])} />
    <div className="upload-icon"><CloudUpload /></div><h2>Drop your image here</h2><p>or choose a file from your device</p><button className="primary-button" onClick={() => ref.current?.click()}><Upload /> Browse files</button><span className="file-note">JPG, JPEG, PNG or WebP <i>•</i> Max 25 MB</span>
  </div>
}

function ToolCard({ tool, onClick }: { tool: Tool; onClick: () => void }) { const Icon = tool.icon; return <button className="tool-card" onClick={onClick}><div className={`tool-icon ${tool.color}`}><Icon /></div><span className="tool-title">{tool.name}<ChevronRight className="tool-arrow" /></span><span className="tool-description">{tool.description}</span></button> }

function PreviewPlaceholder({ fileUrl, processedUrl, zoom, background, isProcessing, progress, isComparing, comparePosition, onCompareMove }: {
  fileUrl?: string; processedUrl?: string; zoom: number; background: string
  isProcessing: boolean; progress: number; isComparing: boolean; comparePosition: number; onCompareMove: (pos: number) => void
}) {
  const stageRef = useRef<HTMLDivElement>(null)
  const displayUrl = processedUrl || fileUrl

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isComparing || !stageRef.current) return
    const rect = stageRef.current.getBoundingClientRect()
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    onCompareMove(x * 100)
  }, [isComparing, onCompareMove])

  if (isComparing && fileUrl && processedUrl) {
    return <div ref={stageRef} className={`preview-stage ${background}`} onMouseMove={handleMouseMove}>
      <div className="compare-container" style={{ '--split': `${comparePosition}%` } as React.CSSProperties}>
        <img src={fileUrl} alt="Original" />
        <img src={processedUrl} alt="Processed" className="compare-after" />
        <div className="compare-handle" />
      </div>
      <div className="preview-label">ORIGINAL</div>
      <div className="preview-label processed">PROCESSED</div>
    </div>
  }

  return <div className={`preview-stage ${background}`} style={{ position: 'relative' }}>
    <div className="preview-image-wrap" style={{ transform: `scale(${zoom / 100})` }}>
      {displayUrl
        ? <img src={displayUrl} alt="Image preview" />
        : <div className="sample-image"><div className="sample-sun" /><div className="sample-mountain one" /><div className="sample-mountain two" /><div className="sample-ground" /><span>Preview canvas</span></div>
      }
    </div>
    {fileUrl && <div className="preview-label">{processedUrl ? 'PROCESSED' : 'ORIGINAL'}</div>}
    {isProcessing && <div className="processing-overlay"><div className="processing-spinner"><div className="spinner-ring" /><p>Processing image…</p><div className="progress-bar-wrap"><div className="progress-bar-fill" style={{ width: `${progress}%` }} /></div></div></div>}
  </div>
}

// ── Tool Settings Panels ─────────────────────────────────────────────

function UpscaleSettings({ settings, onChange }: { settings: any; onChange: (s: any) => void }) {
  return <>
    <div className="setting-section"><div className="section-title"><span>Scale factor</span></div>
      <div className="scale-buttons">
        <button className={settings.scaleFactor === 2 ? 'selected' : ''} onClick={() => onChange({ ...settings, scaleFactor: 2 })}>2× Upscale</button>
        <button className={settings.scaleFactor === 4 ? 'selected' : ''} onClick={() => onChange({ ...settings, scaleFactor: 4 })}>4× Upscale</button>
      </div>
    </div>
    <div className="checkbox-row"><input type="checkbox" id="face-enhance" checked={settings.faceEnhance} onChange={(e) => onChange({ ...settings, faceEnhance: e.target.checked })} /><label htmlFor="face-enhance">Enhance faces</label></div>
  </>
}

function SharpenSettings({ settings, onChange }: { settings: any; onChange: (s: any) => void }) {
  return <>
    <div className="slider-row"><div className="slider-header"><span>Intensity</span><span className="value">{settings.intensity}%</span></div>
      <input className="range" type="range" min="0" max="100" value={settings.intensity} onChange={(e) => onChange({ ...settings, intensity: Number(e.target.value) })} />
    </div>
    <div className="slider-row"><div className="slider-header"><span>Radius</span><span className="value">{settings.radius.toFixed(1)}</span></div>
      <input className="range" type="range" min="5" max="50" value={settings.radius * 10} onChange={(e) => onChange({ ...settings, radius: Number(e.target.value) / 10 })} />
    </div>
  </>
}

function DenoiseSettings({ settings, onChange }: { settings: any; onChange: (s: any) => void }) {
  return <div className="slider-row"><div className="slider-header"><span>Strength</span><span className="value">{settings.strength}%</span></div>
    <input className="range" type="range" min="0" max="100" value={settings.strength} onChange={(e) => onChange({ ...settings, strength: Number(e.target.value) })} />
  </div>
}

function ColorSettings({ settings, onChange }: { settings: any; onChange: (s: any) => void }) {
  const sliders = [
    { key: 'brightness', label: 'Brightness' },
    { key: 'contrast', label: 'Contrast' },
    { key: 'saturation', label: 'Saturation' },
    { key: 'exposure', label: 'Exposure' },
    { key: 'warmth', label: 'Warmth' },
  ] as const
  return <>{sliders.map((s) => <div className="slider-row" key={s.key}><div className="slider-header"><span>{s.label}</span><span className="value">{settings[s.key]}</span></div>
    <input className="range" type="range" min="-100" max="100" value={settings[s.key]} onChange={(e) => onChange({ ...settings, [s.key]: Number(e.target.value) })} />
  </div>)}</>
}

function BackgroundRemoveSettings({ settings, onChange }: { settings: any; onChange: (s: any) => void }) {
  return <div className="checkbox-row"><input type="checkbox" id="alpha-matting" checked={settings.alphaMatting} onChange={(e) => onChange({ ...settings, alphaMatting: e.target.checked })} /><label htmlFor="alpha-matting">Alpha matting (finer edges)</label></div>
}

function BackgroundChangeSettings({ settings, onChange }: { settings: any; onChange: (s: any) => void }) {
  return <>
    <div className="setting-section"><div className="section-title"><span>Background type</span></div>
      <div className="scale-buttons">
        {(['color', 'gradient', 'blur', 'transparent'] as const).map((t) => <button key={t} className={settings.bgType === t ? 'selected' : ''} onClick={() => onChange({ ...settings, bgType: t })}>{t.charAt(0).toUpperCase() + t.slice(1)}</button>)}
      </div>
    </div>
    {settings.bgType === 'color' && <div className="color-picker-row"><label>Background color</label><input type="color" value={settings.bgColor} onChange={(e) => onChange({ ...settings, bgColor: e.target.value })} /></div>}
    {settings.bgType === 'gradient' && <>
      <div className="color-picker-row"><label>Start</label><input type="color" value={settings.gradientStart} onChange={(e) => onChange({ ...settings, gradientStart: e.target.value })} /></div>
      <div className="color-picker-row"><label>End</label><input type="color" value={settings.gradientEnd} onChange={(e) => onChange({ ...settings, gradientEnd: e.target.value })} /></div>
    </>}
    {settings.bgType === 'blur' && <div className="slider-row"><div className="slider-header"><span>Blur amount</span><span className="value">{settings.blurAmount}</span></div>
      <input className="range" type="range" min="1" max="50" value={settings.blurAmount} onChange={(e) => onChange({ ...settings, blurAmount: Number(e.target.value) })} />
    </div>}
  </>
}

function FaceEnhanceSettings({ settings, onChange }: { settings: any; onChange: (s: any) => void }) {
  return <div className="setting-section"><div className="section-title"><span>Output scale</span></div>
    <div className="scale-buttons">
      <button className={settings.upscale === 1 ? 'selected' : ''} onClick={() => onChange({ ...settings, upscale: 1 })}>1× Same size</button>
      <button className={settings.upscale === 2 ? 'selected' : ''} onClick={() => onChange({ ...settings, upscale: 2 })}>2× Enhanced</button>
    </div>
  </div>
}

function BatchSettings({ settings, onChange, batchFiles, onAddFiles, onRemoveFile }: {
  settings: any; onChange: (s: any) => void; batchFiles: File[]; onAddFiles: (files: FileList) => void; onRemoveFile: (i: number) => void
}) {
  const ref = useRef<HTMLInputElement>(null)
  return <>
    <div className="setting-section"><div className="section-title"><span>Operation</span></div>
      <select className="select-dropdown" value={settings.operation} onChange={(e) => onChange({ ...settings, operation: e.target.value })}>
        <option value="sharpen">Sharpen</option><option value="denoise">Denoise</option><option value="background_remove">Remove Background</option>
        <option value="upscale">Upscale</option><option value="face_enhance">Face Enhance</option><option value="color_adjust">Color Adjust</option>
      </select>
    </div>
    <div className="setting-section"><div className="section-title"><span>Images ({batchFiles.length}/20)</span></div>
      <input ref={ref} type="file" accept="image/*" multiple hidden onChange={(e) => { if (e.target.files) onAddFiles(e.target.files) }} />
      <button className="ghost-button" onClick={() => ref.current?.click()} style={{ width: '100%', justifyContent: 'center', marginBottom: 8 }}><Plus /> Add images</button>
      <div className="batch-files">{batchFiles.map((f, i) => <div key={i} className="batch-file-item"><span>{f.name}</span><span className="file-size">{(f.size / 1024).toFixed(0)} KB</span><button className="icon-button" onClick={() => onRemoveFile(i)}><X /></button></div>)}</div>
    </div>
  </>
}

// ── Workspace ────────────────────────────────────────────────────────

function Workspace({ tool, fileUrl, onFile, onExport, imageId, processedUrl, processedInfo, isProcessing, progress, onProcess, outputFormat, setOutputFormat, toolSettings, setToolSettings, processingTimeMs, batchFiles, onAddBatchFiles, onRemoveBatchFile }: {
  tool: string; fileUrl?: string; onFile: (file: File) => void; onExport: () => void
  imageId?: string; processedUrl?: string; processedInfo?: ImageInfo; isProcessing: boolean; progress: number
  onProcess: () => void; outputFormat: string; setOutputFormat: (f: string) => void
  toolSettings: any; setToolSettings: (s: any) => void; processingTimeMs?: number
  batchFiles: File[]; onAddBatchFiles: (files: FileList) => void; onRemoveBatchFile: (i: number) => void
}) {
  const [zoom, setZoom] = useState(72)
  const [background, setBackground] = useState('checkerboard')
  const [isComparing, setIsComparing] = useState(false)
  const [comparePosition, setComparePosition] = useState(50)
  const fileInput = useRef<HTMLInputElement>(null)
  const activeTool = tools.find((item) => item.name === tool) ?? tools[0]
  const isBatch = tool === 'Batch Processing'

  // Map nav items to their settings panel
  const settingsPanel = useMemo(() => {
    switch (tool) {
      case 'AI Upscaler': return <UpscaleSettings settings={toolSettings} onChange={setToolSettings} />
      case 'Image Sharpener': return <SharpenSettings settings={toolSettings} onChange={setToolSettings} />
      case 'Denoise': case 'Noise Reduction': return <DenoiseSettings settings={toolSettings} onChange={setToolSettings} />
      case 'Color Enhancer': case 'Adjustments': return <ColorSettings settings={toolSettings} onChange={setToolSettings} />
      case 'Remove Background': case 'Background Remover': case 'Transparent PNG': return <BackgroundRemoveSettings settings={toolSettings} onChange={setToolSettings} />
      case 'Change Background': case 'Background Changer': return <BackgroundChangeSettings settings={toolSettings} onChange={setToolSettings} />
      case 'Face Enhancer': return <FaceEnhanceSettings settings={toolSettings} onChange={setToolSettings} />
      case 'Batch Processing': return <BatchSettings settings={toolSettings} onChange={setToolSettings} batchFiles={batchFiles} onAddFiles={onAddBatchFiles} onRemoveFile={onRemoveBatchFile} />
      default: return null
    }
  }, [tool, toolSettings, setToolSettings, batchFiles, onAddBatchFiles, onRemoveBatchFile])

  const canProcess = isBatch ? batchFiles.length > 0 : !!imageId

  // Dimensions display
  const dimLabel = useMemo(() => {
    if (processedInfo) return `${processedInfo.width} × ${processedInfo.height} px`
    if (fileUrl && imageId) return 'Uploaded'
    return '2400 × 1600 px'
  }, [processedInfo, fileUrl, imageId])

  return <section className="editor-workspace"><div className="workspace-toolbar"><div className="crumb"><span>Workspace</span><ChevronRight /><strong>{activeTool.name}</strong></div><div className="workspace-controls">{processedUrl && fileUrl && <button className={`ghost-button ${isComparing ? 'active' : ''}`} onClick={() => setIsComparing(!isComparing)}><ArrowLeftRight /> {isComparing ? 'Exit compare' : 'Compare'}</button>}<button className="icon-button"><Expand /></button></div></div><div className="editor-grid"><div className="canvas-column"><PreviewPlaceholder fileUrl={fileUrl} processedUrl={processedUrl} zoom={zoom} background={background} isProcessing={isProcessing} progress={progress} isComparing={isComparing} comparePosition={comparePosition} onCompareMove={setComparePosition} /><div className="canvas-footer"><div className="zoom-control"><button className="icon-button" onClick={() => setZoom(Math.max(25, zoom - 10))}><Minus /></button><span>{zoom}%</span><button className="icon-button" onClick={() => setZoom(Math.min(150, zoom + 10))}><Plus /></button></div><button className="ghost-button" onClick={() => setZoom(72)}>Fit to screen</button><span className="dimensions">{dimLabel}</span></div></div><aside className="settings-panel"><div className="settings-heading"><div><span className="eyebrow">TOOL SETTINGS</span><h3>{activeTool.name}</h3></div><button className="icon-button"><MoreHorizontal /></button></div>{!fileUrl && !isBatch && <div className="panel-alert"><Lightbulb /><span>Add an image to unlock the preview controls.</span></div>}{settingsPanel}<div className="setting-section"><div className="section-title"><span>Output format</span></div>
    <select className="select-dropdown" value={outputFormat} onChange={(e) => setOutputFormat(e.target.value)}>
      <option value="png">PNG</option><option value="jpeg">JPEG</option><option value="webp">WebP</option>
    </select>
  </div><div className="setting-section"><div className="section-title"><span>Preview background</span><CircleHelp /></div><div className="background-options"><button className={background === 'checkerboard' ? 'selected' : ''} onClick={() => setBackground('checkerboard')}><span className="checker" />Transparent</button><button className={background === 'white' ? 'selected' : ''} onClick={() => setBackground('white')}><span className="white-swatch" />White</button><button className={background === 'black' ? 'selected' : ''} onClick={() => setBackground('black')}><span className="black-swatch" />Black</button></div></div>{processingTimeMs != null && <div className="processing-time"><Timer /> Completed in {(processingTimeMs / 1000).toFixed(1)}s</div>}{processedInfo && <div className="image-info"><div className="image-info-item"><strong>{processedInfo.width}×{processedInfo.height}</strong>Resolution</div><div className="image-info-item"><strong>{processedInfo.format.toUpperCase()}</strong>Format</div><div className="image-info-item"><strong>{(processedInfo.size_bytes / 1024).toFixed(0)} KB</strong>Size</div></div>}<button className="process-button" onClick={onProcess} disabled={!canProcess || isProcessing}><Sparkles /> {isProcessing ? 'Processing…' : 'Process image'}</button><input ref={fileInput} type="file" accept="image/*" hidden onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} /></aside></div></section>
}

function ExportModal({ onClose, fileUrl, processedUrl, processedInfo, imageId }: {
  onClose: () => void; fileUrl?: string; processedUrl?: string; processedInfo?: ImageInfo; imageId?: string
}) {
  const [format, setFormat] = useState(processedInfo?.format?.toUpperCase() || 'PNG')
  const [quality, setQuality] = useState(90)
  const [filename, setFilename] = useState('my-enhanced-image')

  const download = () => {
    const url = processedInfo ? api.imageUrl(processedInfo.id) : (processedUrl || fileUrl)
    if (!url) { alert('No image to export.'); return }
    const a = document.createElement('a')
    a.href = url
    a.download = `${filename}.${format.toLowerCase()}`
    a.click()
    onClose()
  }

  const w = processedInfo?.width ?? ''
  const h = processedInfo?.height ?? ''

  return <div className="modal-backdrop" onClick={onClose}><div className="export-modal" onClick={(e) => e.stopPropagation()}><div className="modal-header"><div><span className="eyebrow">EXPORT IMAGE</span><h2>Save your image</h2></div><button className="icon-button" onClick={onClose}><X /></button></div><label>File name<div className="input-like"><FileImage /> <input value={filename} onChange={(e) => setFilename(e.target.value)} /><span>.{format.toLowerCase()}</span></div></label><div className="form-row"><label>Format<div className="format-options">{['PNG', 'JPG', 'WebP'].map((item) => <button key={item} className={format === item ? 'selected' : ''} onClick={() => setFormat(item)}>{format === item && <Check />}{item}</button>)}</div></label></div><div className="form-row two-col"><label>Width<div className="input-like"><input defaultValue={w} /><span>px</span></div></label><label>Height<div className="input-like"><input defaultValue={h} /><span>px</span></div></label></div><div className="quality-row"><div><span>Quality</span><strong>{quality}%</strong></div><input className="range" type="range" value={quality} onChange={(e) => setQuality(Number(e.target.value))} /></div><div className="transparent-note"><Check /> Transparent background will be preserved in PNG</div><div className="modal-actions"><button className="ghost-button" onClick={onClose}>Cancel</button><button className="primary-button" onClick={download}><Download /> Download image</button></div></div></div>
}

// ── Toast System ─────────────────────────────────────────────────────

function ToastContainer({ toasts }: { toasts: Toast[] }) {
  return <div className="toast-container">{toasts.map((t) => <div key={t.id} className={`toast ${t.type}`}>{t.type === 'success' ? <Check /> : t.type === 'error' ? <X /> : <Lightbulb />}<span>{t.message}</span></div>)}</div>
}

// ── Default tool settings ────────────────────────────────────────────

function getDefaultSettings(tool: string) {
  switch (tool) {
    case 'AI Upscaler': return { scaleFactor: 4, faceEnhance: false }
    case 'Image Sharpener': return { intensity: 50, radius: 1.0 }
    case 'Denoise': case 'Noise Reduction': return { strength: 50 }
    case 'Color Enhancer': case 'Adjustments': return { brightness: 0, contrast: 0, saturation: 0, exposure: 0, warmth: 0 }
    case 'Remove Background': case 'Background Remover': case 'Transparent PNG': return { alphaMatting: false }
    case 'Change Background': case 'Background Changer': return { bgType: 'color', bgColor: '#ffffff', gradientStart: '#000000', gradientEnd: '#ffffff', blurAmount: 15 }
    case 'Face Enhancer': return { upscale: 1 }
    case 'Batch Processing': return { operation: 'sharpen' }
    default: return {}
  }
}

// ── Main Page ────────────────────────────────────────────────────────

export default function Page() {
  // Core state
  const [collapsed, setCollapsed] = useState(false)
  const [active, setActive] = useState('Dashboard')
  const [fileUrl, setFileUrl] = useState<string>()
  const [showExport, setShowExport] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [theme, setTheme] = useState<'light' | 'dark'>('light')

  // Backend state
  const [imageId, setImageId] = useState<string>()
  const [originalImageId, setOriginalImageId] = useState<string>()
  const [processedUrl, setProcessedUrl] = useState<string>()
  const [processedInfo, setProcessedInfo] = useState<ImageInfo>()
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [outputFormat, setOutputFormat] = useState('png')
  const [toolSettings, setToolSettings] = useState<any>({})
  const [processingTimeMs, setProcessingTimeMs] = useState<number>()
  const [backendOnline, setBackendOnline] = useState(false)

  // History (undo/redo)
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)

  // Batch files
  const [batchFiles, setBatchFiles] = useState<File[]>([])

  // Toasts
  const [toasts, setToasts] = useState<Toast[]>([])
  const toastIdRef = useRef(0)

  const addToast = useCallback((type: Toast['type'], message: string) => {
    const id = ++toastIdRef.current
    setToasts((prev) => [...prev, { id, type, message }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000)
  }, [])

  // Check backend health periodically
  useEffect(() => {
    let mounted = true
    const check = () => {
      api.health()
        .then(() => { if (mounted) setBackendOnline(true) })
        .catch(() => { if (mounted) setBackendOnline(false) })
    }
    check()
    const interval = setInterval(check, 3000)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  // Reset tool settings when switching tools
  useEffect(() => {
    setToolSettings(getDefaultSettings(active))
    setProcessedUrl(undefined)
    setProcessedInfo(undefined)
    setProcessingTimeMs(undefined)
  }, [active])

  // Handle file upload
  const handleFile = useCallback(async (file: File) => {
    const localUrl = URL.createObjectURL(file)
    setFileUrl(localUrl)
    setProcessedUrl(undefined)
    setProcessedInfo(undefined)
    setProcessingTimeMs(undefined)
    setActive('AI Upscaler')

    try {
      const info = await api.upload(file)
      setImageId(info.id)
      setOriginalImageId(info.id)
      setBackendOnline(true)
      addToast('success', `Uploaded ${file.name} (${info.width}×${info.height})`)

      // Push to history
      const entry: HistoryEntry = { imageId: info.id, imageUrl: localUrl, label: 'Original', width: info.width, height: info.height, format: info.format, sizeBytes: info.size_bytes }
      setHistory([entry])
      setHistoryIndex(0)
    } catch (e: any) {
      addToast('error', `Upload failed: ${e.message}. Ensure backend is running.`)
    }
  }, [addToast])

  // Handle processing result from a job-based endpoint
  const handleJobResult = useCallback(async (jobResponse: JobResponse, toolLabel: string) => {
    const completed = await pollJob(jobResponse.job_id, (j) => setProgress(j.progress))
    setIsProcessing(false)

    if (completed.status === 'completed' && completed.result?.success && completed.result.image) {
      const img = completed.result.image
      const url = api.imageUrl(img.id)
      setProcessedUrl(url)
      setProcessedInfo(img)
      setImageId(img.id)
      setProcessingTimeMs(completed.result.processing_time_ms ?? undefined)
      addToast('success', `${toolLabel} complete`)

      // Push to history
      setHistory((prev) => {
        const trimmed = prev.slice(0, historyIndex + 1)
        return [...trimmed, { imageId: img.id, imageUrl: url, label: toolLabel, width: img.width, height: img.height, format: img.format, sizeBytes: img.size_bytes, processingTimeMs: completed.result?.processing_time_ms ?? undefined }]
      })
      setHistoryIndex((prev) => prev + 1)
    } else {
      addToast('error', completed.result?.error || completed.error || 'Processing failed')
    }
  }, [addToast, historyIndex])

  // Handle processing result from a direct endpoint
  const handleDirectResult = useCallback((result: ProcessingResult, toolLabel: string) => {
    setIsProcessing(false)

    if (result.success && result.image) {
      const img = result.image
      const url = api.imageUrl(img.id)
      setProcessedUrl(url)
      setProcessedInfo(img)
      setImageId(img.id)
      setProcessingTimeMs(result.processing_time_ms ?? undefined)
      addToast('success', `${toolLabel} complete`)

      setHistory((prev) => {
        const trimmed = prev.slice(0, historyIndex + 1)
        return [...trimmed, { imageId: img.id, imageUrl: url, label: toolLabel, width: img.width, height: img.height, format: img.format, sizeBytes: img.size_bytes, processingTimeMs: result.processing_time_ms ?? undefined }]
      })
      setHistoryIndex((prev) => prev + 1)
    } else {
      addToast('error', result.error || 'Processing failed')
    }
  }, [addToast, historyIndex])

  // Process image
  const handleProcess = useCallback(async () => {
    if (!backendOnline) { addToast('error', 'Backend is offline'); return }

    const isBatch = active === 'Batch Processing'
    if (!isBatch && !imageId) { addToast('error', 'Upload an image first'); return }
    if (isBatch && batchFiles.length === 0) { addToast('error', 'Add images first'); return }

    setIsProcessing(true)
    setProgress(0)

    try {
      switch (active) {
        case 'AI Upscaler': {
          const res = await api.upscale(imageId!, { scale_factor: toolSettings.scaleFactor, face_enhance: toolSettings.faceEnhance, output_format: outputFormat })
          await handleJobResult(res, 'Upscale')
          break
        }
        case 'Image Sharpener': {
          const res = await api.sharpen(imageId!, { intensity: toolSettings.intensity, radius: toolSettings.radius, output_format: outputFormat })
          handleDirectResult(res, 'Sharpen')
          break
        }
        case 'Denoise': case 'Noise Reduction': {
          const res = await api.denoise(imageId!, { strength: toolSettings.strength, output_format: outputFormat })
          handleDirectResult(res, 'Denoise')
          break
        }
        case 'Face Enhancer': {
          const res = await api.faceEnhance(imageId!, { upscale: toolSettings.upscale, output_format: outputFormat })
          await handleJobResult(res, 'Face enhance')
          break
        }
        case 'Color Enhancer': case 'Adjustments': {
          const res = await api.colorAdjust(imageId!, { ...toolSettings, output_format: outputFormat })
          handleDirectResult(res, 'Color adjust')
          break
        }
        case 'Remove Background': case 'Background Remover': case 'Transparent PNG': {
          const fmt = active === 'Transparent PNG' ? 'png' : outputFormat
          const res = await api.backgroundRemove(imageId!, { alpha_matting: toolSettings.alphaMatting, output_format: fmt })
          await handleJobResult(res, 'Background remove')
          break
        }
        case 'Change Background': case 'Background Changer': {
          const res = await api.backgroundChange(imageId!, {
            bg_type: toolSettings.bgType,
            bg_color: toolSettings.bgColor,
            gradient_start: toolSettings.gradientStart,
            gradient_end: toolSettings.gradientEnd,
            blur_amount: toolSettings.blurAmount,
            original_image_id: originalImageId,
            output_format: outputFormat,
          })
          await handleJobResult(res, 'Background change')
          break
        }
        case 'Batch Processing': {
          const res = await api.batchProcess(batchFiles, toolSettings.operation)
          await handleJobResult(res, 'Batch processing')
          break
        }
        default:
          addToast('info', `${active} processing not implemented yet`)
          setIsProcessing(false)
      }
    } catch (e: any) {
      setIsProcessing(false)
      addToast('error', e.message || 'Processing failed')
    }
  }, [active, imageId, originalImageId, backendOnline, toolSettings, outputFormat, batchFiles, addToast, handleJobResult, handleDirectResult])

  // Undo/Redo
  const canUndo = historyIndex > 0
  const canRedo = historyIndex < history.length - 1

  const handleUndo = useCallback(() => {
    if (!canUndo) return
    const newIdx = historyIndex - 1
    const entry = history[newIdx]
    setHistoryIndex(newIdx)
    setImageId(entry.imageId)
    setProcessedUrl(newIdx === 0 ? undefined : entry.imageUrl)
    setProcessedInfo(newIdx === 0 ? undefined : { id: entry.imageId, width: entry.width, height: entry.height, format: entry.format, size_bytes: entry.sizeBytes, filename: '' })
    setProcessingTimeMs(entry.processingTimeMs)
    if (newIdx === 0) { setFileUrl(entry.imageUrl) }
  }, [canUndo, historyIndex, history])

  const handleRedo = useCallback(() => {
    if (!canRedo) return
    const newIdx = historyIndex + 1
    const entry = history[newIdx]
    setHistoryIndex(newIdx)
    setImageId(entry.imageId)
    setProcessedUrl(entry.imageUrl)
    setProcessedInfo({ id: entry.imageId, width: entry.width, height: entry.height, format: entry.format, size_bytes: entry.sizeBytes, filename: '' })
    setProcessingTimeMs(entry.processingTimeMs)
  }, [canRedo, historyIndex, history])

  // Batch file management
  const handleAddBatchFiles = useCallback((files: FileList) => {
    setBatchFiles((prev) => [...prev, ...Array.from(files)].slice(0, 20))
  }, [])
  const handleRemoveBatchFile = useCallback((i: number) => {
    setBatchFiles((prev) => prev.filter((_, idx) => idx !== i))
  }, [])

  const isDashboard = active === 'Dashboard' || active === 'Recent Projects' || active === 'All Images'

  return <main className={`app-shell ${theme}-mode`}>
    <Topbar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} onExport={() => setShowExport(true)} theme={theme} onThemeToggle={() => setTheme(theme === 'light' ? 'dark' : 'light')} canUndo={canUndo} canRedo={canRedo} onUndo={handleUndo} onRedo={handleRedo} backendOnline={backendOnline} />
    <div className="mobile-bar"><button className="icon-button" onClick={() => setMobileOpen(!mobileOpen)}><Menu /></button><span>{active}</span></div>
    <div className="app-body"><div className={mobileOpen ? 'mobile-sidebar-open' : ''}><Sidebar collapsed={collapsed} active={active} onSelect={(name) => { setActive(name); setMobileOpen(false) }} /></div><div className="main-content">
      {isDashboard ? <>
        <section className="dashboard-header"><div><span className="eyebrow">CREATIVE WORKSPACE</span><h1>Your Image Workspace</h1><p>Enhance, upscale, and transform your images.</p></div><div className="header-status"><span className={`status-badge ${backendOnline ? 'connected' : 'disconnected'}`}><span className="dot" />{backendOnline ? 'All systems operational' : 'Backend offline'}</span></div></section>
        <UploadCard onFile={handleFile} />
        <div className="section-header"><div><h2>Start with a tool</h2><p>Professional image tools, right in your browser.</p></div><button className="filter-button">All tools <ChevronDown /></button></div>
        <div className="tools-grid">{tools.map((tool) => <ToolCard key={tool.name} tool={tool} onClick={() => { setActive(TOOL_NAV_MAP[tool.name] || tool.name) }} />)}</div>
        <div className="tip-card"><div className="tip-icon"><Lightbulb /></div><div><strong>Everything runs locally</strong><p>Your images never leave your device. This open-source prototype is private by design.</p></div><button className="icon-button"><ChevronRight /></button></div>
      </> : <Workspace
        tool={active}
        fileUrl={fileUrl}
        onFile={handleFile}
        onExport={() => setShowExport(true)}
        imageId={imageId}
        processedUrl={processedUrl}
        processedInfo={processedInfo}
        isProcessing={isProcessing}
        progress={progress}
        onProcess={handleProcess}
        outputFormat={outputFormat}
        setOutputFormat={setOutputFormat}
        toolSettings={toolSettings}
        setToolSettings={setToolSettings}
        processingTimeMs={processingTimeMs}
        batchFiles={batchFiles}
        onAddBatchFiles={handleAddBatchFiles}
        onRemoveBatchFile={handleRemoveBatchFile}
      />}
    </div></div>
    {showExport && <ExportModal onClose={() => setShowExport(false)} fileUrl={fileUrl} processedUrl={processedUrl} processedInfo={processedInfo} imageId={imageId} />}
    <ToastContainer toasts={toasts} />
  </main>
}

# Biblicus Dashboard Roadmap

## Priority 1: Core Functionality Fixes

### 1.1 Fix Metadata Display
**Status**: Critical Bug
**Description**: Metadata sidebar incorrectly shows "no extractions" and "no analysis" for Alfa corpus despite existing data.

**Tasks**:
- Investigate metadata API endpoints to ensure they're reading from correct paths
- Fix extraction listing to detect and display extracted snapshots
- Fix analysis listing to detect and display analysis runs (Markov, topic modeling, etc.)
- Ensure proper fallback/error handling when metadata is missing

**Acceptance Criteria**:
- Alfa corpus correctly displays all extractions in metadata sidebar
- Analysis results (markov, topic modeling) are visible and accessible
- Recipe files are listed and accessible

---

## Priority 2: Media Type Viewers

### 2.1 Audio Player (MPEG/MP3)
**Status**: High Priority
**Description**: Build audio player for audio/mpeg files in corpus.

**Tasks**:
- Create AudioViewer component with HTML5 audio player
- Add waveform visualization (consider wavesurfer.js or similar)
- Show audio metadata (duration, bitrate, etc.)
- Support playback controls (play/pause, seek, volume, playback speed)
- Display any associated transcription if available

**Libraries to Consider**:
- `wavesurfer.js` - Waveform visualization
- `react-h5-audio-player` - Pre-built audio player component
- Native HTML5 `<audio>` element with custom controls

---

### 2.2 Text File Viewer
**Status**: High Priority
**Description**: Display plain text files with proper formatting.

**Tasks**:
- Create TextViewer component with syntax highlighting
- Support different text encodings
- Add search/find within text
- Consider line numbers and wrapping options
- Handle large files efficiently (virtualization)

**Libraries to Consider**:
- `react-syntax-highlighter` - Syntax highlighting
- `react-window` - Virtualization for large files
- `monaco-editor` (React wrapper) - Full-featured editor if needed

---

### 2.3 Deepgram JSON Viewer
**Status**: High Priority
**Description**: Custom viewer for Deepgram transcription JSON with specialized features.

**Tasks**:
- Parse and display Deepgram JSON structure
- Show transcription text with timestamps
- Display confidence scores per word/utterance
- Highlight speaker diarization if present
- Link to audio timestamps (if audio file available)
- Show metadata (model, language, etc.)

**UI Features**:
- Tabbed view: Transcript / Words / Metadata / Raw JSON
- Interactive timeline with clickable timestamps
- Confidence score visualization (color-coded)

---

### 2.4 Image Viewer
**Status**: Medium Priority
**Description**: Display images with zoom, pan, and metadata.

**Tasks**:
- Create ImageViewer component supporting common formats (PNG, JPG, WebP, etc.)
- Add zoom in/out and pan controls
- Display EXIF metadata if available
- Support image comparison (before/after for processing results)
- Handle large images efficiently

**Libraries to Consider**:
- `react-image-zoom` - Zoom functionality
- `react-photo-view` - Lightbox-style viewer
- `pinch-zoom-element` - Touch-friendly zoom

---

### 2.5 PDF Viewer
**Status**: Medium Priority
**Description**: Render PDF files with navigation and text selection.

**Tasks**:
- Create PDFViewer component with page navigation
- Support text selection and search
- Add zoom controls and page thumbnails
- Display PDF metadata
- Handle large multi-page PDFs efficiently

**Libraries to Consider**:
- `react-pdf` - Widely used, based on PDF.js
- `@react-pdf-viewer` - Feature-rich alternative
- Consider rendering limitations and performance

---

## Priority 3: Recipe Management UI

### 3.1 Recipe Viewer Components
**Status**: Medium Priority
**Description**: Visual components for viewing and managing extraction/analysis recipes.

**Tasks**:
- Create RecipeCard component for listing recipes
- Build RecipeDetailView for viewing recipe configuration
- Support different recipe types (extraction, analysis, retrieval)
- Show recipe metadata (last run, success rate, etc.)
- Display recipe parameters in readable format (YAML/JSON)

**UI Patterns**:
- Cards for recipe list with key info
- Expandable full-screen view for recipe details
- Visual indicators for recipe status/health
- Link to runs that used each recipe

---

## Priority 4: Animation Framework & Visual Design Language

### 4.1 Unified Animation System
**Status**: Design Phase
**Description**: Create cohesive animation framework for drill-down interactions.

**Concept**:
- Multi-column horizontal layout with smooth transitions
- Drill-down pattern: click item → animate/expand to reveal detail
- Breadcrumb or back navigation with reverse animation
- Springy, fluid animations throughout (already using GSAP)

**Design Considerations**:
- Should metadata panel expansion push other content or overlay?
- How do we handle deep nesting (corpus → file → extraction → stage)?
- Mobile/responsive considerations for horizontal layout
- Performance with large datasets

**Tasks**:
- Design mockups/wireframes for navigation patterns
- Create reusable animation components/hooks
- Implement level-based navigation system
- Add breadcrumb or "zoom out" controls
- Ensure animations are performant and accessible

---

## Priority 5: Advanced Extraction Visualization

### 5.1 Multi-Stage Pipeline Viewer
**Status**: Future
**Description**: Visual interface for viewing composite extraction results from multi-stage pipelines.

**Use Case**: View document understanding + OCR results together:
- See layout regions detected by document understanding model
- Overlay OCR text for each region
- Compare against source document
- Enable correction/labeling workflow

**Tasks**:
- Design layout for side-by-side comparison (source + regions + text)
- Implement region highlighting on document preview
- Build text editor for corrections with region association
- Add labeling interface for training data creation
- Export corrected/labeled data

**Technical Challenges**:
- Coordinate system mapping (region boxes to image coordinates)
- Handling different page sizes/resolutions
- Efficient rendering of many regions
- Data model for corrections and labels

---

## Additional Recommended Items

### A. Search & Filter
**Priority**: Medium
**Description**: Add search functionality across files, extractions, and analysis results.

**Features**:
- Full-text search within corpus
- Filter by media type, date, tags
- Search within specific file content
- Saved searches/filters

---

### B. Batch Operations
**Priority**: Low
**Description**: Select multiple files and perform operations.

**Features**:
- Multi-select in file tree
- Batch export, delete, tag
- Bulk re-run extraction/analysis

---

### C. Settings & Configuration
**Priority**: Medium
**Description**: User preferences and app configuration.

**Features**:
- Theme settings (already have Bauhaus design)
- Default media viewers
- Performance settings (virtualization thresholds)
- Keyboard shortcuts
- Corpus root path management

---

### D. Error Handling & Loading States
**Priority**: High
**Description**: Graceful error handling and loading UX throughout app.

**Tasks**:
- Add loading skeletons for all data fetching
- Implement error boundaries
- Show helpful error messages (not just "failed")
- Retry mechanisms for failed requests
- Offline state handling

---

### E. File Tree Enhancements
**Priority**: Medium
**Description**: Improve file tree navigation and features.

**Features**:
- Sort options (name, date, size, type)
- Collapse/expand all folders
- File tree virtualization for large corpora
- Drag & drop support (future)
- Right-click context menu

---

### F. Metadata Enrichment UI
**Priority**: Low
**Description**: Edit/add metadata to files and extractions.

**Features**:
- Add tags to files
- Edit titles and descriptions
- Custom metadata fields
- Bulk metadata editing

---

### G. Export & Sharing
**Priority**: Low
**Description**: Export data and share views.

**Features**:
- Export file lists (CSV, JSON)
- Export analysis results
- Shareable links to specific files/views (if deployed)
- Download original files or processed results

---

### H. Performance Monitoring
**Priority**: Medium
**Description**: Track and display corpus processing status.

**Features**:
- Show extraction progress/status
- Display analysis run history with timing
- Queue status for pending operations
- Resource usage metrics

---

### I. Documentation & Help
**Priority**: Medium
**Description**: In-app help and documentation.

**Features**:
- Tooltip explanations for UI elements
- Help button with contextual docs
- Keyboard shortcut cheatsheet
- Link to external documentation

---

### J. Testing & Quality
**Priority**: High
**Description**: Ensure reliability and maintainability.

**Tasks**:
- Add unit tests for key components
- Integration tests for file viewers
- E2E tests for critical workflows
- Accessibility audit (WCAG compliance)
- Performance testing with large corpora

---

## Technical Debt & Infrastructure

### API Improvements
- Standardize API response format
- Add pagination for large result sets
- Implement caching strategy
- WebSocket support for real-time updates
- API documentation (OpenAPI/Swagger)

### Build & Deploy
- Optimize bundle size
- Add Docker containerization
- CI/CD pipeline
- Environment-specific configs
- Production build optimizations

### Code Quality
- ESLint/Prettier consistency
- TypeScript strict mode
- Component documentation (Storybook?)
- Code splitting by route
- Remove unused dependencies (react-resizable-panels)

---

## Migration Path (Future)

### Cloud Sync (AWS Amplify)
- Currently building for local browsing only
- Future: Optional cloud sync to AWS
- DynamoDB catalog integration (already planned in separate doc)
- S3 storage for large files
- Real-time collaboration features

---

## Notes

- All animations should use GSAP (already integrated)
- Maintain Bauhaus design principles (flat, minimal, no shadows/gradients)
- Use Shadcn UI components consistently
- No backward compatibility / no fallback logic (project policy)
- Progressive enhancement: show what's available, fail gracefully

---

## Next Steps

1. Fix metadata display bug (blocking user work)
2. Implement audio player (highest user need)
3. Add text and Deepgram viewers (common use case)
4. Design animation framework (core to vision)
5. Plan extraction visualization (complex, needs design phase)

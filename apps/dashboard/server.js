#!/usr/bin/env node
/**
 * Local backend API server for browsing Biblicus corpora
 *
 * This server reads from the local filesystem to serve corpus data
 * without needing to sync/copy anything to the cloud.
 *
 * Uses graceful progressive enhancement: displays whatever data is
 * available, skips what's missing. No fallback logic or backward
 * compatibility - implements the current correct approach only.
 */

import express from 'express';
import cors from 'cors';
import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3001;

// Configure corpora root path from environment or default to ../../corpora
const CORPORA_ROOT = process.env.BIBLICUS_CORPORA_ROOT || path.join(__dirname, '..', '..', 'corpora');

app.use(cors());
app.use(express.json());

// Security helper: validate path is within CORPORA_ROOT
function validateCorpusPath(corpusName) {
  const corpusPath = path.join(CORPORA_ROOT, corpusName);
  const resolvedPath = path.resolve(corpusPath);
  const resolvedRoot = path.resolve(CORPORA_ROOT);

  // Ensure path starts with root AND has proper separator (prevents prefix attacks)
  if (!resolvedPath.startsWith(resolvedRoot + path.sep) && resolvedPath !== resolvedRoot) {
    throw new Error('Access denied: path traversal attempt detected');
  }

  return corpusPath;
}

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', corporaRoot: CORPORA_ROOT });
});

// List all available corpora
app.get('/api/corpora', async (req, res) => {
  try {
    const entries = await fs.readdir(CORPORA_ROOT, { withFileTypes: true });

    const corpora = [];
    for (const entry of entries) {
      if (!entry.isDirectory() || entry.name.startsWith('.')) continue;

      const corpusPath = path.join(CORPORA_ROOT, entry.name);

      // Check for metadata directory (current standard)
      const metadataDir = path.join(corpusPath, 'metadata');
      let hasMetadata = false;
      try {
        await fs.access(metadataDir);
        hasMetadata = true;
      } catch (err) {
        // No metadata directory - will show basic info only
      }

      // If no metadata, check for legacy .biblicus (for identification only)
      if (!hasMetadata) {
        const biblicusDir = path.join(corpusPath, '.biblicus');
        try {
          await fs.access(biblicusDir);
          // Has legacy structure, treat as corpus
        } catch (err) {
          // Not a corpus at all, skip it
          continue;
        }
      }

      // Read basic info
      const stats = await fs.stat(corpusPath);
      const corpus = {
        name: entry.name,
        path: corpusPath,
        lastModified: stats.mtime,
        hasMetadata,
      };

      // Try to read catalog.json from metadata folder
      if (hasMetadata) {
        const catalogPath = path.join(corpusPath, 'metadata', 'catalog.json');
        try {
          const catalogData = await fs.readFile(catalogPath, 'utf8');
          const catalog = JSON.parse(catalogData);
          corpus.itemCount = Object.keys(catalog.items || {}).length;
          corpus.schemaVersion = catalog.schema_version;
          corpus.configurationId = catalog.configuration_id;
        } catch (err) {
          // Catalog missing or invalid - show what we have
          corpus.itemCount = 0;
        }
      }

      corpora.push(corpus);
    }

    res.json({ corpora });
  } catch (error) {
    console.error('Error listing corpora:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get details for a specific corpus
app.get('/api/corpora/:name', async (req, res) => {
  try {
    const corpusPath = validateCorpusPath(req.params.name);

    // Check corpus exists
    await fs.access(corpusPath);

    const corpus = {
      name: req.params.name,
      path: corpusPath,
    };

    // Read catalog.json from metadata folder
    const catalogPath = path.join(corpusPath, 'metadata', 'catalog.json');
    try {
      const catalogData = await fs.readFile(catalogPath, 'utf8');
      corpus.catalog = JSON.parse(catalogData);
    } catch (err) {
      // No catalog - show what we can
      corpus.catalog = null;
    }

    // List extraction snapshots
    const extractedDir = path.join(corpusPath, 'extracted');
    try {
      const snapshots = await fs.readdir(extractedDir);
      corpus.extractionSnapshots = snapshots.filter(s => !s.startsWith('.'));
    } catch (err) {
      corpus.extractionSnapshots = [];
    }

    res.json(corpus);
  } catch (error) {
    console.error('Error reading corpus:', error);
    res.status(404).json({ error: 'Corpus not found' });
  }
});

// Get catalog items for a corpus with optional filters
app.get('/api/corpora/:name/catalog', async (req, res) => {
  try {
    const corpusPath = validateCorpusPath(req.params.name);
    const catalogPath = path.join(corpusPath, 'metadata', 'catalog.json');

    const catalogData = await fs.readFile(catalogPath, 'utf8');
    const catalog = JSON.parse(catalogData);

    // Convert items object to array
    let items = Object.values(catalog.items || {});

    // Apply filters
    const { tag, mediaType, search } = req.query;

    if (tag) {
      items = items.filter(item => item.tags && item.tags.includes(tag));
    }

    if (mediaType) {
      items = items.filter(item => item.media_type === mediaType);
    }

    if (search) {
      const searchLower = search.toLowerCase();
      items = items.filter(item =>
        (item.title && item.title.toLowerCase().includes(searchLower)) ||
        (item.relpath && item.relpath.toLowerCase().includes(searchLower))
      );
    }

    res.json({ items, total: items.length });
  } catch (error) {
    console.error('Error reading catalog:', error);
    res.status(404).json({ error: 'Catalog not found' });
  }
});

// Get a specific catalog item
app.get('/api/corpora/:name/catalog/:itemId', async (req, res) => {
  try {
    const corpusPath = validateCorpusPath(req.params.name);
    const catalogPath = path.join(corpusPath, 'metadata', 'catalog.json');

    const catalogData = await fs.readFile(catalogPath, 'utf8');
    const catalog = JSON.parse(catalogData);

    const item = catalog.items?.[req.params.itemId];

    if (!item) {
      return res.status(404).json({ error: 'Item not found' });
    }

    res.json(item);
  } catch (error) {
    console.error('Error reading catalog item:', error);
    res.status(404).json({ error: 'Item not found' });
  }
});

// List extraction snapshots for a corpus
app.get('/api/corpora/:name/snapshots', async (req, res) => {
  try {
    const corpusPath = validateCorpusPath(req.params.name);
    const extractedDir = path.join(corpusPath, 'extracted');

    const snapshots = await fs.readdir(extractedDir);
    const snapshotDetails = [];

    for (const snapshot of snapshots) {
      if (snapshot.startsWith('.')) continue;

      const snapshotPath = path.join(extractedDir, snapshot);
      const manifestPath = path.join(snapshotPath, 'manifest.json');

      try {
        const manifestData = await fs.readFile(manifestPath, 'utf8');
        const manifest = JSON.parse(manifestData);

        snapshotDetails.push({
          id: snapshot,
          ...manifest
        });
      } catch (err) {
        // Manifest doesn't exist, just include basic info
        const stats = await fs.stat(snapshotPath);
        snapshotDetails.push({
          id: snapshot,
          createdAt: stats.birthtime,
        });
      }
    }

    res.json({ snapshots: snapshotDetails });
  } catch (error) {
    console.error('Error reading snapshots:', error);
    res.status(404).json({ error: 'Snapshots not found' });
  }
});

// List analysis runs for a corpus
app.get('/api/corpora/:name/analysis', async (req, res) => {
  try {
    const corpusPath = validateCorpusPath(req.params.name);
    const analysisDir = path.join(corpusPath, 'analysis');

    const analysisRuns = [];

    try {
      const analysisTypes = await fs.readdir(analysisDir);

      for (const analysisType of analysisTypes) {
        if (analysisType.startsWith('.')) continue;

        const typePath = path.join(analysisDir, analysisType);
        const typeStat = await fs.stat(typePath);

        if (!typeStat.isDirectory()) continue;

        const runs = await fs.readdir(typePath);

        for (const run of runs) {
          if (run.startsWith('.')) continue;

          const runPath = path.join(typePath, run);
          const runStat = await fs.stat(runPath);

          if (!runStat.isDirectory()) continue;

          analysisRuns.push({
            id: run,
            type: analysisType,
            createdAt: runStat.birthtime,
            path: `${analysisType}/${run}`,
          });
        }
      }
    } catch (err) {
      // No analysis directory
    }

    res.json({ analysisRuns });
  } catch (error) {
    console.error('Error reading analysis runs:', error);
    res.status(404).json({ error: 'Analysis runs not found' });
  }
});

// List recipes for a corpus
app.get('/api/corpora/:name/recipes', async (req, res) => {
  try {
    const corpusPath = validateCorpusPath(req.params.name);
    const recipesDir = path.join(corpusPath, 'recipes');

    const recipes = [];

    async function scanRecipes(dir, prefix = '') {
      try {
        const entries = await fs.readdir(dir, { withFileTypes: true });

        for (const entry of entries) {
          if (entry.name.startsWith('.')) continue;

          const fullPath = path.join(dir, entry.name);
          const relativePath = prefix ? `${prefix}/${entry.name}` : entry.name;

          if (entry.isDirectory()) {
            await scanRecipes(fullPath, relativePath);
          } else if (entry.name.endsWith('.yml') || entry.name.endsWith('.yaml')) {
            recipes.push({
              name: entry.name,
              path: relativePath,
              type: prefix || 'general',
            });
          }
        }
      } catch (err) {
        // Directory doesn't exist or can't be read
      }
    }

    await scanRecipes(recipesDir);

    res.json({ recipes });
  } catch (error) {
    console.error('Error reading recipes:', error);
    res.status(404).json({ error: 'Recipes not found' });
  }
});

// Get configuration
app.get('/api/config', (req, res) => {
  res.json({
    corporaRoot: CORPORA_ROOT,
  });
});

// Update configuration (set corpora root)
app.post('/api/config', async (req, res) => {
  try {
    const { corporaRoot } = req.body;

    if (!corporaRoot) {
      return res.status(400).json({ error: 'corporaRoot is required' });
    }

    // Validate the path exists
    await fs.access(corporaRoot);

    // Save to config file
    const configPath = path.join(__dirname, '.corpus-viewer.json');
    await fs.writeFile(configPath, JSON.stringify({ corporaRoot }, null, 2));

    res.json({ success: true, corporaRoot });
  } catch (error) {
    console.error('Error updating config:', error);
    res.status(400).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`\n🚀 Biblicus Corpus Viewer API Server`);
  console.log(`   Running on http://localhost:${PORT}`);
  console.log(`   Corpora root: ${CORPORA_ROOT}`);
  console.log(`\nEndpoints:`);
  console.log(`   GET  /api/corpora                    - List all corpora`);
  console.log(`   GET  /api/corpora/:name              - Get corpus details`);
  console.log(`   GET  /api/corpora/:name/catalog      - List catalog items`);
  console.log(`   GET  /api/corpora/:name/snapshots    - List extraction snapshots`);
  console.log(`   GET  /api/corpora/:name/analysis     - List analysis runs`);
  console.log(`   GET  /api/corpora/:name/recipes      - List recipes`);
  console.log(`   GET  /api/config                     - Get configuration`);
  console.log(`   POST /api/config                     - Set corpora root path\n`);
});

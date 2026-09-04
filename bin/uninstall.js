#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

console.log('🗑️  Uninstalling arch-wiki-es AI Skill...\n');

const homeDir = os.homedir();
const targets = [
    // Antigravity AI Agent
    { name: 'Antigravity AI Agent (~/.gemini/antigravity/skills/arch-wiki-es)', path: path.join(homeDir, '.gemini', 'antigravity', 'skills', 'arch-wiki-es') },
    { name: 'Antigravity Config (~/.gemini/config/skills/arch-wiki-es)', path: path.join(homeDir, '.gemini', 'config', 'skills', 'arch-wiki-es') },
    
    // Claude Code
    { name: 'Claude Code (~/.claude/skills/arch-wiki-es)', path: path.join(homeDir, '.claude', 'skills', 'arch-wiki-es') },
    
    // Cursor AI
    { name: 'Cursor AI (~/.cursor/skills/arch-wiki-es)', path: path.join(homeDir, '.cursor', 'skills', 'arch-wiki-es') },
    
    // Local Workspace Targets
    { name: 'Local Workspace (.skills/arch-wiki-es)', path: path.join(process.cwd(), '.skills', 'arch-wiki-es') },
    { name: 'Local Workspace (.agents/skills/arch-wiki-es)', path: path.join(process.cwd(), '.agents', 'skills', 'arch-wiki-es') },

    // Legacy arch-wiki folders (for clean migration)
    { name: 'Legacy arch-wiki (~/.gemini/antigravity/skills/arch-wiki)', path: path.join(homeDir, '.gemini', 'antigravity', 'skills', 'arch-wiki') },
    { name: 'Legacy arch-wiki (~/.gemini/config/skills/arch-wiki)', path: path.join(homeDir, '.gemini', 'config', 'skills', 'arch-wiki') },
    { name: 'Legacy arch-wiki (~/.claude/skills/arch-wiki)', path: path.join(homeDir, '.claude', 'skills', 'arch-wiki') },
    { name: 'Legacy arch-wiki (~/.cursor/skills/arch-wiki)', path: path.join(homeDir, '.cursor', 'skills', 'arch-wiki') },
    { name: 'Legacy arch-wiki (.skills/arch-wiki)', path: path.join(process.cwd(), '.skills', 'arch-wiki') }
];

let removedCount = 0;

targets.forEach(target => {
    try {
        if (fs.existsSync(target.path)) {
            fs.rmSync(target.path, { recursive: true, force: true });
            console.log(`✅ Removed from ${target.name}:`);
            console.log(`   └─ ${target.path}\n`);
            removedCount++;
        }
    } catch (err) {
        console.warn(`⚠️ Could not remove ${target.name}: ${err.message}`);
    }
});

if (removedCount > 0) {
    console.log(`🎉 Uninstallation complete! Removed ${removedCount} skill directories.`);
} else {
    console.log('ℹ️  No installed arch-wiki-es (or legacy arch-wiki) directories were found.');
}

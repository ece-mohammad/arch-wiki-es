#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

// Support --uninstall flag
if (process.argv.includes('--uninstall') || process.argv.includes('-u')) {
    require('./uninstall.js');
    process.exit(0);
}

console.log('🏛️  Installing arch-wiki-es AI Skill...\n');

const rootDir = path.join(__dirname, '..');
const skillFile = path.join(rootDir, 'SKILL.md');
const templateFile = path.join(rootDir, 'templates', 'build_html.py');
const overrideExampleFile = path.join(rootDir, 'templates', 'embedded-overrides.example.json');

if (!fs.existsSync(skillFile)) {
    console.error('❌ Error: SKILL.md not found in package root.');
    process.exit(1);
}

const homeDir = os.homedir();

// 1. Clean up legacy 'arch-wiki' installation directories if they exist
const legacyDirs = [
    path.join(homeDir, '.gemini', 'antigravity', 'skills', 'arch-wiki'),
    path.join(homeDir, '.gemini', 'config', 'skills', 'arch-wiki'),
    path.join(homeDir, '.claude', 'skills', 'arch-wiki'),
    path.join(homeDir, '.cursor', 'skills', 'arch-wiki'),
    path.join(process.cwd(), '.skills', 'arch-wiki')
];

legacyDirs.forEach(dir => {
    try {
        if (fs.existsSync(dir)) {
            fs.rmSync(dir, { recursive: true, force: true });
            console.log(`🧹 Cleaned up legacy arch-wiki skill directory:\n   └─ ${dir}\n`);
        }
    } catch (e) {
        // Ignore permission warnings on cleanup
    }
});

// 2. Skill Targets for arch-wiki-es
const targets = [];

// Antigravity Global Skills Paths
targets.push({ name: 'Antigravity AI Agent (~/.gemini/antigravity/skills/arch-wiki-es)', path: path.join(homeDir, '.gemini', 'antigravity', 'skills', 'arch-wiki-es') });
targets.push({ name: 'Antigravity Config (~/.gemini/config/skills/arch-wiki-es)', path: path.join(homeDir, '.gemini', 'config', 'skills', 'arch-wiki-es') });

// Claude Code Skills Path
targets.push({ name: 'Claude Code (~/.claude/skills/arch-wiki-es)', path: path.join(homeDir, '.claude', 'skills', 'arch-wiki-es') });

// Cursor AI Skills Path
targets.push({ name: 'Cursor AI (~/.cursor/skills/arch-wiki-es)', path: path.join(homeDir, '.cursor', 'skills', 'arch-wiki-es') });

// Local Workspace Target (if run inside a target project)
if (process.cwd() !== rootDir) {
    targets.push({ name: 'Local Project Workspace (.skills/arch-wiki-es)', path: path.join(process.cwd(), '.skills', 'arch-wiki-es') });
    targets.push({ name: 'Local Project Workspace (.agents/skills/arch-wiki-es)', path: path.join(process.cwd(), '.agents', 'skills', 'arch-wiki-es') });
}

let installedCount = 0;

targets.forEach(target => {
    try {
        if (!fs.existsSync(target.path)) {
            fs.mkdirSync(target.path, { recursive: true });
        }
        
        // Copy SKILL.md
        fs.copyFileSync(skillFile, path.join(target.path, 'SKILL.md'));
        
        // Copy build_html.py if templates exist
        if (fs.existsSync(templateFile)) {
            const templatesDir = path.join(target.path, 'templates');
            if (!fs.existsSync(templatesDir)) {
                fs.mkdirSync(templatesDir, { recursive: true });
            }
            fs.copyFileSync(templateFile, path.join(templatesDir, 'build_html.py'));
        }

        if (fs.existsSync(overrideExampleFile)) {
            const templatesDir = path.join(target.path, 'templates');
            if (!fs.existsSync(templatesDir)) {
                fs.mkdirSync(templatesDir, { recursive: true });
            }
            fs.copyFileSync(overrideExampleFile, path.join(templatesDir, 'embedded-overrides.example.json'));
        }

        console.log(`✅ Installed arch-wiki-es to ${target.name}:`);
        console.log(`   └─ ${target.path}\n`);
        installedCount++;
    } catch (err) {
        console.warn(`⚠️ Could not write to ${target.name}: ${err.message}`);
    }
});

if (installedCount > 0) {
    console.log('🎉 arch-wiki-es Skill Installation Complete!');
    console.log('\n💡 Usage in AI Chat / Agent:');
    console.log('   Simply prompt your AI assistant:');
    console.log('   "Run arch-wiki-es skill to generate architecture documentation for this project"\n');
} else {
    console.error('❌ Skill installation failed. Please check folder permissions.');
}

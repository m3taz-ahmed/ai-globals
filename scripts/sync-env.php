<?php

/**
 * Global AI Env Sync Script
 * 
 * Synchronizes keys from .env to .env.example, .env.staging, and .env.production.
 * It appends missing keys with empty values, preserving existing comments and values.
 */

if ($argc < 2) {
    echo "Usage: php sync-env.php <project-directory>\n";
    exit(1);
}

$projectDir = rtrim($argv[1], '/\\');
$envPath = $projectDir . DIRECTORY_SEPARATOR . '.env';

if (!file_exists($envPath)) {
    echo "Skipping env sync: No .env file found in $projectDir\n";
    exit(0); // Not an error, just nothing to do
}

function parseEnvKeys($filePath) {
    $keys = [];
    if (!file_exists($filePath)) return $keys;
    
    $lines = file($filePath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        $line = trim($line);
        if (strpos($line, '#') === 0) continue; // Skip comments
        
        $parts = explode('=', $line, 2);
        if (count($parts) === 2) {
            $key = trim($parts[0]);
            // only match valid env keys
            if (preg_match('/^[a-zA-Z_][a-zA-Z0-9_]*$/', $key)) {
                $keys[] = $key;
            }
        }
    }
    return $keys;
}

function syncEnvFile($sourceKeys, $targetPath) {
    $targetKeys = parseEnvKeys($targetPath);
    $missingKeys = array_diff($sourceKeys, $targetKeys);
    
    if (empty($missingKeys)) {
        return false; // Nothing to add
    }
    
    $content = "";
    if (file_exists($targetPath)) {
        $content = file_get_contents($targetPath);
        // Ensure file ends with newline before appending
        if (!empty($content) && substr($content, -1) !== "\n") {
            $content .= "\n";
        }
    }
    
    $content .= "\n# Added automatically by Global AI Sync\n";
    foreach ($missingKeys as $key) {
        $content .= "{$key}=\n";
    }
    
    file_put_contents($targetPath, $content);
    return true;
}

$sourceKeys = parseEnvKeys($envPath);

$targets = [
    '.env.example',
    '.env.staging',
    '.env.production'
];

$exampleModified = false;

foreach ($targets as $targetFile) {
    $targetPath = $projectDir . DIRECTORY_SEPARATOR . $targetFile;
    $modified = syncEnvFile($sourceKeys, $targetPath);
    
    if ($modified) {
        echo "Synced new keys to $targetFile\n";
    }
    
    if ($targetFile === '.env.example' && $modified) {
        $exampleModified = true;
    }
}

// Automatically stage .env.example if we modified it
if ($exampleModified) {
    echo "Staging .env.example for commit...\n";
    $gitCommand = sprintf('cd "%s" && git add .env.example', $projectDir);
    exec($gitCommand);
}

exit(0);

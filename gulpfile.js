#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const gulp = require('gulp');
const workDir = process.cwd();
const pathToFolder = path.join(workDir, 'themes-default');
const exec = require('child_process').execSync;

const build = done => {
    // Place code for your default task here
    done();
};

const getFolders = dir => {
    return fs.readdirSync(dir)
        .filter(function(file) {
            return fs.statSync(path.join(dir, file)).isDirectory();
        });
};

const lintTheme = theme => {
    console.log(`Starting lint of ${theme}`);
    console.log(`Working dir: ${process.cwd()}`);
    let result;
    try {
        result = exec('yarn', {cwd: theme});
        console.log(`Lint errored with: ${result}`);
    } catch (err) {
        console.log(`Lint errored for theme ${theme} with error:\n${err.stdout.toString()}`);
        process.exit(err.status);
    }
};

gulp.task('default', ['lint']);
gulp.task('build', build);
gulp.task('lintthemes', cb => {
    const folders = getFolders(pathToFolder);
    folders.map(folder => {
        const fullPath = path.join(pathToFolder, folder);
        process.chdir(fullPath);
        return lintTheme(fullPath);
    });
    cb();
});


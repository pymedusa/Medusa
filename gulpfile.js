const path = require('path');
const babelify = require('babelify');
const runSequence = require('run-sequence');
const livereload = require('gulp-livereload');
const sourcemaps = require('gulp-sourcemaps');
const gulpif = require('gulp-if');
const xo = require('gulp-xo');
const gulp = require('gulp');
const source = require('vinyl-source-stream');
const uglify = require('gulp-uglify-es').default;
const browserify = require('browserify');
const buffer = require('vinyl-buffer');
const changed = require('gulp-changed');
const flatMap = require('gulp-flatmap');
const imagemin = require('gulp-imagemin');
const pngquant = require('imagemin-pngquant');
const postcss = require('gulp-postcss');
const sass = require('gulp-sass');
const cssnano = require('cssnano');
const autoprefixer = require('autoprefixer');
const reporter = require('postcss-reporter');

const PROD = process.env.NODE_ENV === 'production';

const processors = [
    reporter({
        clearMessages: true
    }),
    autoprefixer()
];

if (PROD) {
    processors.push(cssnano());
}

const staticAssets = [
    'static/browserconfig.xml',
    'static/favicon.ico',
    'static/manifest.json',
    'static/fonts/**/*',
    'static/js/lib/**/*',
    'static/js/vender.js',
    'static/js/vender.min.js',
    'static/css/lib/*.css',
    'static/css/**/*.min.css',
    'static/css/lib/images/**/**',
    'static/**/**.ttf'
];

gulp.task('default', ['build']);

gulp.task('build', done => {
    runSequence('lint', ['css', 'img', 'js', 'static'], async () => {
        if (!PROD) {
            done();
        }
    });
});

gulp.task('watch', ['build'], () => {
    livereload.listen({ port: 35729 });
    gulp.watch('static/img/**/*', ['img']);
    gulp.watch('static/css/**/*.scss', ['css']);
    gulp.watch([
        'static/js/**/*.js',
        '!static/js/lib/**',
        '!static/js/*.min.js',
        '!static/js/vender.js'
    ], ['js']);
});

gulp.task('img', () => {
    return gulp
    .src('static/images/**/*', {
        base: 'static/images'
    })
    .pipe(changed('build/images'))
    .pipe(
      imagemin({
          progressive: true,
          svgoPlugins: [{ removeViewBox: false }, { cleanupIDs: false }],
          use: [pngquant()]
      })
    )
    .pipe(gulp.dest('build/images'))
    .pipe(gulpif(!PROD, livereload({ port: 35729 })))
    .pipe(gulpif(PROD, gulp.dest('build/images')));
});

gulp.task('css', () => {
    return gulp.src([
        'static/css/**/*.css',
        '!static/css/**/*.min.css'
    ], {
        base: 'static'
    })
    .pipe(changed('build'))
    .pipe(sourcemaps.init())
    .pipe(sass().on('error', sass.logError))
    .pipe(postcss(processors))
    .pipe(sourcemaps.write('./'))
    .pipe(gulp.dest('build'))
    .pipe(gulpif(!PROD, livereload({ port: 35729 })));
});

gulp.task('lint', () => {
    return gulp.src([
        'static/js/**/*.js',
        '!static/js/lib/**',
        '!static/js/*.min.js',
        '!static/js/vender.js'
    ], {
        base: 'static'
    })
    .pipe(changed('build'))
    .pipe(xo())
    .pipe(xo.format())
    .pipe(xo.failAfterError());
});

gulp.task('js', ['lint'], () => {
    return gulp.src([
        'static/js/**/*.js',
        '!static/js/lib/**',
        '!static/js/*.min.js',
        '!static/js/vender.js'
    ], {
        base: 'static',
        read: false
    })
    .pipe(changed('build'))
    .pipe(flatMap((stream, file) => {
        const cleanPath = file.path.replace(path.join(process.cwd(), 'static/'), '');
        console.log('changed: ' + file.path.replace(process.cwd() + '/', ''));
        return browserify({
            entries: file.path,
            debug: true
        })
        .transform(babelify)
        .bundle()
        .pipe(source(cleanPath))
        .pipe(buffer())
        .pipe(sourcemaps.init({ loadMaps: true }))
        .pipe(uglify())
        .pipe(sourcemaps.write('./'))
        .pipe(gulp.dest('build'))
        .pipe(gulpif(!PROD, livereload({ port: 35729 })));
    }));
});

gulp.task('static', () => {
    return gulp
    .src(staticAssets, {
        base: 'static'
    })
    .pipe(gulp.dest('build'));
});

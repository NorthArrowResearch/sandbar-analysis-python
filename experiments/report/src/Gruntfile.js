module.exports = function(grunt) {
  grunt.initConfig({

    // Grunt-sass 
    // sass (libsass) config
    sass: {
        options: {
            sourceMap: true,
            relativeAssets: false,
            outputStyle: 'compressed',
            sassDir: 'scss',
            cssDir: '../assets/css',
            includePaths: [
              'node_modules/foundation-sites/scss',
              'node_modules/font-awesome/scss',
            ]
        },
        build: {
            files: [{
                expand: true,
                cwd: 'scss/',
                src: ['**/*.scss'],
                dest: '../assets/css',
                ext: '.css'
            }]
        }
    },

    // Watch a file(s) for changes
    watch: {
        scss: {
            files: ['scss/**/*'],
            tasks: ['sass'],
            options: {
                spawn: false,
            },
        },
        scripts: {
            files: ['js/**/*.js'],
            tasks: ['concat',],
            options: {
                spawn: false,
            },
        },
    },

    // Grunt-concat: Concatenate files (mostly javascript)
    concat: {
        options: {
            separator: ';\n\n',
        },
        dist: {
            src: [
                'node_modules/jquery/dist/jquery.min.js',
                'node_modules/foundation-sites/dist/js/foundation.min.js', 
                'node_modules/selectize/dist/js/standalone/selectize.min.js',
                'node_modules/d3/build/d3.min.js', 
                'node_modules/spin.js/spin.min.js',
                'js/toc.js',
                'js/plots.js',
                'js/app.js'
            ],
            dest: '../assets/js/dist.js',
        },
    },    


    copy: {
        jquerymap: {
            expand: true,
            cwd: 'node_modules/jquery/dist',
            src: 'jquery.min.map',
            dest: '../assets/js',
        },
        themes: {
            files: [{
              expand: true,
              cwd: 'node_modules/selectize/dist/css',
              src: 'selectize.bootstrap3.css',
              rename: function(dest, src) {
                return 'scss/_selectize-bootstrap3.scss';
              }
            }],
          },        
        fonts: {
            files: [{ expand:true, cwd:'node_modules/font-awesome/fonts/', src:'*', dest: '../assets/fonts' }],
        }

    },      

  });

  // Define the modules we need for these tasks:
  grunt.loadNpmTasks('grunt-sass');
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-contrib-concat');
  grunt.loadNpmTasks('grunt-contrib-watch');

  // Here are our tasks 
  grunt.registerTask('default', [ 'build' ]);
  grunt.registerTask('build', [ 'copy', 'sass', 'concat', 'copy:jquerymap', 'copy:jquerymap' ]);
  grunt.registerTask('dev', [ 'watch' ]);

};
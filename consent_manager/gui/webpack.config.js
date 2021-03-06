//require our dependencies
let path = require('path');
let webpack = require('webpack');
let BundleTracker = require('webpack-bundle-tracker');

module.exports = {
    mode: 'development',
    context: __dirname,
    entry: './assets/js/index',
    output: {
        path: path.resolve(__dirname, './assets/bundles/'),
        filename: 'webpack.js',
    },
    plugins: [
        //tells webpack where to store data about your bundles.
        new BundleTracker({filename: './webpack-stats.json'}),
        //makes jQuery available in every module
        new webpack.ProvidePlugin({
            $: 'jquery',
            jQuery: 'jquery',
            'window.jQuery': 'jquery'  // TODO: is it necessary?
        })
    ],
    module: {
        rules: [
            {
                test: /\.jsx?$/,
                exclude: /node_modules/,
                loader: 'babel-loader',
                query: {
                    presets: ['react']
                }
            },
            {
                test: /(\.css|\.scss)$/,
                loaders: ['style-loader', 'css-loader', 'sass-loader']
            },
            {
                test: /\.(ttf|eot|svg)(\?v=[0-9]\.[0-9]\.[0-9])?$/,
                loader: "file-loader"
            },
            {
                test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/,
                loader: "url-loader?limit=10000&mimetype=application/font-woff"
            }
        ]
    },
    resolve: {
        modules: ['node_modules'],
        extensions: ['.js', '.jsx']
    }
};
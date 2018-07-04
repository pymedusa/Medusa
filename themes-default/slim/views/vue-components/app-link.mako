<script type="text/x-template" id="app-link-template">
    <component
        :is="linkProperties.is"
        :to="linkProperties.to"
        :href="linkProperties.href"
        :target="linkProperties.target"
        :rel="linkProperties.rel"
        :false-link="linkProperties.falseLink"
    >
        <slot></slot>
    </component>
</script>
<script>
Vue.component('app-link', {
    template: '#app-link-template',
    store,
    props: {
        to: [String, Object],
        href: String,
        indexerId: {
            type: String
        },
        placeholder: {
            type: String,
            default: 'indexer-to-name'
        },
        base: String
    },
    computed: {
        config() {
            return this.$store.state.config;
        },
        indexerName() {
            const { config, indexerId } = this;
            const { indexers } = config.indexers.config;
            if (!indexerId) return undefined;
            // Returns `undefined` if not found
            return Object.keys(indexers).find(indexer => indexers[indexer].id === parseInt(indexerId, 10));
        },
        computedBase() {
            // Return prop before HTML element to allow tests to mock
            if (this.base) {
                return this.base;
            }

            return document.getElementsByTagName('base')[0].getAttribute('href');
        },
        computedHref() {
            const { href, indexerId, placeholder, indexerName } = this;
            if (indexerId && placeholder) {
                return href.replace(placeholder, indexerName);
            }
            return href;
        },
        isIRC() {
            return this.computedHref.startsWith('irc://');
        },
        isAbsolute() {
            const href = this.computedHref;
            return /^[a-z][a-z0-9+.-]*:/.test(href);
        },
        isExternal() {
            const base = this.computedBase;
            const href = this.computedHref;
            return !href.startsWith(base) && !href.startsWith('webcal://');
        },
        isHashPath() {
            return this.computedHref.startsWith('#');
        },
        anonymisedHref() {
            const { anonRedirect } = this.config;
            const href = this.computedHref;
            return anonRedirect ? anonRedirect + href : href;
        },
        linkProperties() {
            const { to, isIRC, isAbsolute, isExternal, isHashPath, isAnonymised, anonymisedHref } = this;
            const base = this.computedBase;
            const href = this.computedHref;

            // Return normal router-link
            if (to) {
                return {
                    is: 'router-link',
                    to: { name: href }
                };
            }

            // Just return a boring link with other attrs
            // @NOTE: This is for scroll achors as it uses the id
            if (!href) {
                return {
                    is: 'a',
                    falseLink: true
                };
            }

            return {
                is: 'a',
                target: isAbsolute && isExternal ? '_blank' : '_self',
                href: (() => {
                    if (isHashPath) {
                        const { location } = window;
                        if (location.hash.length === 0) {
                            // Current location might be `url#`
                            const newHash = location.href.endsWith('#') ? href.substr(1) : href;
                            return location.href + newHash;
                        }
                        return location.href.replace(location.hash, '') + href;
                    }
                    if (isIRC) {
                        return href;
                    }
                    if (isAbsolute) {
                        if (isExternal) {
                            return anonymisedHref;
                        }
                        return href;
                    }
                    return new URL(href, base).href;
                })(),
                rel: isAbsolute && isExternal ? 'noreferrer' : undefined
            };
        }
    }
});
</script>
<style>
/* @NOTE: This fixes the header blocking elements when using a hash link */
/* e.g. displayShow?indexername=tvdb&seriesid=83462#season-5  */
[false-link]:before { content: ''; display: block; position: relative; width: 0; height: 100px; margin-top: -100px }
</style>

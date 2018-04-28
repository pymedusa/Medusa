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
    name: 'app-link',
    props: {
        to: [String, Object],
        href: String,
        indexerId: {
            type: String
        },
        placeholder: {
            type: String,
            default: 'indexer-to-name'
        }
    },
    computed: {
        linkProperties() {
            const {to, indexerId, placeholder} = this;
            const href = indexerId && placeholder ? this.href.replace(placeholder, MEDUSA.config.indexers.indexerIdToName(indexerId)) : this.href;
            const base = document.getElementsByTagName('base')[0].getAttribute('href');
            const isIRC = url => {
                return url.startsWith('irc://');
            };
            const isAbsolute = url => {
                return /^[a-z][a-z0-9+.-]*:/.test(url);
            }
            const isExternal = url => {
                return !url.startsWith(base);
            };
            const isHashPath = url => {
                return url.startsWith('#')
            };
            const isAnonymised = url => {
                return url.startsWith(MEDUSA.config.anonRedirect);
            };
            const anonymise = url => MEDUSA.config.anonRedirect ? MEDUSA.config.anonRedirect + url : null;
            if (!to) {
                if (href) {
                    // @TODO: Remove this once we move to vue only
                    if (isAnonymised(href)) {
                        throw new Error('Still using anon_url in Python!');
                    }
                    const resolvedHref = () => {
                        if (isHashPath(href)) {
                            return window.location.href + href;
                        }
                        if (isIRC(href)) {
                            return href;
                        }
                        if (isAbsolute(href)) {
                            if (isExternal(href)) {
                                return anonymise(href)
                            } else {
                                return href;
                            }
                        } else {
                            return new URL(href, base).href
                        }
                    };
                    return {
                        is: 'a',
                        target: isAbsolute(href) && isExternal(href) ? '_blank' : '_self',
                        href: resolvedHref(),
                        rel: isAbsolute(href) && isExternal(href) ? 'noreferrer' : undefined
                    };
                }

                // Just return a boring link with other attrs
                // @NOTE: This is for scroll achors as it uses the id
                return {
                    is: 'a',
                    falseLink: true
                };
            }
            return {
                is: 'router-link',
                to: { name: href }
            };
        }
    },
    template: `#app-link-template`
});
</script>
<style>
/* @NOTE: This fixes the header blocking elements when using a hash link */
/* e.g. displayShow?indexername=tvdb&seriesid=83462#season-5  */
[false-link]:before { content: ''; display: block; position: relative; width: 0; height: 100px; margin-top: -100px }
</style>

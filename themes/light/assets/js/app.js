(window.webpackJsonp=window.webpackJsonp||[]).push([[3],{286:function(e,o,t){"use strict";t.r(o);var n=t(5),a=t(30),s=t(24),i=t(23),d=t(1),c=t(4);n.default.config.devtools=!0,n.default.config.performance=!0,Object(a.c)(),Object(a.b)();const l=new n.default({name:"app",router:s.b,store:i.a,data:()=>({globalLoading:!1,pageComponent:!1}),computed:{...Object(d.f)({showsLoading:e=>e.shows.loading})},mounted(){const{getShows:e,setLoadingDisplay:o,setLoadingFinished:t}=this;if(c.g&&console.log("App Mounted!"),!window.location.pathname.includes("/login")){const{$store:e}=this;Promise.all([e.dispatch("login",{username:window.username}),e.dispatch("getConfig"),e.dispatch("getStats")]).then(([e,o])=>{c.g&&console.log("App Loaded!");const t=new CustomEvent("medusa-config-loaded",{detail:{general:o.general,layout:o.layout}});window.dispatchEvent(t)}).catch(e=>{console.debug(e),alert("Unable to connect to Medusa!")})}e().then(()=>{console.log("Finished loading all shows."),setTimeout(()=>{t(!0),o(!1)},2e3)})},methods:{...Object(d.c)({getShows:"getShows"}),...Object(d.e)(["setLoadingDisplay","setLoadingFinished"])}}).$mount("#vue-wrap");o.default=l}},[[286,1,0,2]]]);
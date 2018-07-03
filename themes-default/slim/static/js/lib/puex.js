(function (global, factory) {
	typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports, require('vue')) :
	typeof define === 'function' && define.amd ? define(['exports', 'vue'], factory) :
	(factory((global.puex = {}),global.Vue));
}(this, (function (exports,Vue) { 'use strict';

Vue = Vue && Vue.hasOwnProperty('default') ? Vue['default'] : Vue;

function normalizeMap(map) {
  return Array.isArray(map) ? map.map(function (k) { return ({ k: k, v: k }); }) : Object.keys(map).map(function (k) { return ({ k: k, v: map[k] }); });
}

function resolveSource(source, type) {
  return typeof type === 'function' ? type : source[type];
}

var createMapState = function (_store) { return function (states) {
  var res = {};
  var loop = function () {
    var _ref = list[i];

    var k = _ref.k;
    var v = _ref.v;

    res[k] = function () {
      var store = _store || this.$store;
      return typeof v === 'function' ? v.call(this, store.state) : store.state[v];
    };
  };

  for (var i = 0, list = normalizeMap(states); i < list.length; i += 1) loop();
  return res;
}; };

var mapToMethods = function (sourceName, runnerName, _store) { return function (map) {
  var res = {};
  var loop = function () {
    var _ref2 = list[i];

    var k = _ref2.k;
    var v = _ref2.v;

    res[k] = function (payload) {
      var store = _store || this.$store;
      var source = store[sourceName];
      var runner = store[runnerName];
      var actualSource = typeof v === 'function' ? v.call(this, source) : v;
      return runner.call(store, actualSource, payload);
    };
  };

  for (var i = 0, list = normalizeMap(map); i < list.length; i += 1) loop();
  return res;
}; };

var devtoolHook = typeof window !== 'undefined' && window.__VUE_DEVTOOLS_GLOBAL_HOOK__;

function devtoolPlugin(store) {
  if (!devtoolHook) { return; }

  store._devtoolHook = devtoolHook;

  devtoolHook.emit('vuex:init', store);

  devtoolHook.on('vuex:travel-to-state', function (targetState) {
    store.replaceState(targetState);
  });

  store.subscribe(function (mutation, state) {
    devtoolHook.emit('vuex:mutation', mutation, state);
  });
}

var Store = function Store(ref) {
  var this$1 = this;
  if ( ref === void 0 ) ref = {};
  var state = ref.state;
  var mutations = ref.mutations; if ( mutations === void 0 ) mutations = {};
  var actions = ref.actions; if ( actions === void 0 ) actions = {};
  var plugins = ref.plugins;
  var subscribers = ref.subscribers; if ( subscribers === void 0 ) subscribers = [];

  this.vm = new Vue({
    data: {
      $$state: typeof state === 'function' ? state() : state
    }
  });
  this.mutations = mutations;
  this.actions = actions;
  this.subscribers = subscribers;

  if (plugins) {
    plugins.forEach(function (p) { return this$1.use(p); });
  }

  if (Vue.config.devtools) {
    this.getters = []; // hack for vue-devtools
    devtoolPlugin(this);
  }

  this.mapState = createMapState(this);
  this.mapActions = mapToMethods('actions', 'dispatch', this);
  this.mapMutations = mapToMethods('mutations', 'commit', this);
};

var prototypeAccessors = { state: { configurable: true } };

Store.install = function install (Vue$$1) {
  Vue$$1.mixin({
    beforeCreate: function beforeCreate() {
      this.$store = this.$options.store || this.$parent && this.$parent.$store;
    }
  });
};

prototypeAccessors.state.get = function () {
  return this.vm.$data.$$state;
};

prototypeAccessors.state.set = function (v) {
  {
    throw new Error('[puex] store.state is read-only, use store.replaceState(state) instead');
  }
};

Store.prototype.subscribe = function subscribe (sub) {
    var this$1 = this;

  this.subscribers.push(sub);
  return function () { return this$1.subscribers.splice(this$1.subscribers.indexOf(sub), 1); };
};

Store.prototype.commit = function commit (type, payload) {
    var this$1 = this;

  var mutation = resolveSource(this.mutations, type);
  mutation && mutation(this.state, payload);
  for (var i = 0, list = this$1.subscribers; i < list.length; i += 1) {
    var sub = list[i];

      sub({ type: type, payload: payload }, this$1.state);
  }
};

Store.prototype.dispatch = function dispatch (type, payload) {
  var action = resolveSource(this.actions, type);
  var ctx = {
    dispatch: this.dispatch.bind(this),
    commit: this.commit.bind(this)
  };
  return Promise.resolve(action && action(ctx, payload));
};

Store.prototype.use = function use (fn) {
  fn(this);
  return this;
};

Store.prototype.replaceState = function replaceState (state) {
  this.vm.$data.$$state = state;
  return this;
};

Object.defineProperties( Store.prototype, prototypeAccessors );

var mapState = createMapState();
var mapActions = mapToMethods('actions', 'dispatch');
var mapMutations = mapToMethods('mutations', 'commit');

exports['default'] = Store;
exports.mapState = mapState;
exports.mapActions = mapActions;
exports.mapMutations = mapMutations;

Object.defineProperty(exports, '__esModule', { value: true });

})));

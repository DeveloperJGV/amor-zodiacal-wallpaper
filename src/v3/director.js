'use strict';

// Director de "Amor Zodiacal v3". Va pegado a la capa base (sólida, a pantalla completa)
// y anima todas las demás capas. Los datos (nombres de capas, posiciones, caminos de
// cometas, morse) los genera build_scene.py y los inyecta aquí.
const D = /*DATA*/null;

const T = 30;          // el ciclo de animación dura 30 s, igual que la v2
const H = D.H;
const DRAW = 2.4, HOLD = 3.4, FADE = 1.6;

let L = {};
let mode = { anniv: false, valentine: false, night: false };
let modeTimer = 0;
let intensity = 1.0;
let showMessages = true;
let taps = [];
let tapNext = 0;
let flashes = [];
let flashNext = 0;

function sm(x) {
	x = Math.min(Math.max(x, 0), 1);
	return x * x * (3 - 2 * x);
}

function refreshMode() {
	const d = new Date();
	const m = d.getMonth() + 1, day = d.getDate(), h = d.getHours();
	mode.anniv = (m === 10 && day === 18);     // aniversario de boda
	mode.valentine = (m === 2 && day === 14);
	mode.night = (h >= 22 || h < 6);
}

function morseLevel(t) {
	const n = D.morse.units.length;
	const u = (t / D.morse.unit) % n;
	const i = Math.floor(u);
	const on = D.morse.units[i];
	const prv = D.morse.units[(i + n - 1) % n];
	const edge = 0.04 / D.morse.unit;
	const f = u - i;
	return f < edge ? prv + (on - prv) * sm(f / edge) : on;
}

export function applyUserProperties(props) {
	if (props.hasOwnProperty('intensidad')) intensity = props.intensidad;
	if (props.hasOwnProperty('mensajes')) showMessages = props.mensajes;
}

export function init(value) {
	for (const n of D.layers) {
		L[n] = thisScene.getLayer(n);
	}
	for (const n of D.taps) taps.push({ n: n, age: 99 });
	for (const n of D.flashes) flashes.push({ n: n, age: 99 });
	refreshMode();
	return value;
}

function setAlpha(n, a) {
	const l = L[n];
	if (l) l.alpha = Math.max(0, a);
}

function setScale(n, s) {
	const l = L[n];
	if (l) l.scale = new Vec3(s, s, 1);
}

function setPos(n, x, y) {
	const l = L[n];
	if (l) l.origin = new Vec3(x, y, 0);
}

export function update(value) {
	const dt = engine.frametime;
	const t = engine.runtime % T;
	modeTimer -= dt;
	if (modeTimer <= 0) {
		refreshMode();
		modeTimer = 20;
	}
	const k = intensity * (mode.night ? 0.75 : 1.0);
	const waveY = -500 + (H + 1000) * ((2 * t / T) % 1);   // en coordenadas de imagen (y hacia abajo)

	// estrellas: titileo + ola de luz
	for (const s of D.sparks) {
		const u = (s.f * t / T + s.ph) % 1;
		const tw = Math.pow(Math.sin(Math.PI * u), 10);
		const wave = Math.exp(-Math.pow((s.y - waveY) / 260, 2));
		setAlpha(s.g, k * s.z * (0.08 + 0.92 * tw + 0.45 * wave));
	}
	// corazones: latido "pum-pum"
	const hb = mode.valentine || mode.anniv ? 1.6 : 1.0;
	for (const h of D.hearts) {
		const u = (h.f * t / T + h.ph) % 1;
		const b = Math.exp(-Math.pow(u / 0.022, 2)) + 0.65 * Math.exp(-Math.pow((u - 0.08) / 0.025, 2)) + Math.exp(-Math.pow((u - 1) / 0.022, 2));
		const s = 1 + 0.07 * b * hb;
		setScale(h.n, s);
		setScale(h.g, s);
		const wave = Math.exp(-Math.pow((h.y - waveY) / 260, 2));
		setAlpha(h.g, k * h.z * (0.15 + 0.85 * b * hb + 0.4 * wave));
	}
	// Géminis y Capricornio brillan por turnos
	for (const g of D.signs) {
		const br = 0.5 + 0.5 * Math.sin(2 * Math.PI * (3 * t / T + (g.gem ? 0 : 0.5)));
		const wave = Math.exp(-Math.pow((g.y - waveY) / 260, 2));
		setAlpha(g.g, k * g.z * (0.1 + 0.5 * br + 0.7 * wave));
	}
	// morse: "TE AMO"
	setAlpha(D.morse.layer, morseLevel(t));

	// constelaciones
	const msgs = mode.anniv ? D.annivMsgs : D.msgs;
	for (const m of D.allMsgs) {
		const active = showMessages && msgs.indexOf(m.id) >= 0;
		const dtm = ((t - m.t0) % T + T) % T;
		const life = DRAW + HOLD + FADE;
		const on = active && dtm < life;
		const fadeAll = on ? 1 - sm((dtm - DRAW - HOLD) / FADE) : 0;
		setAlpha(m.halo, 0.9 * fadeAll * sm(dtm / 0.6));
		const n = m.glyphs.length;
		for (let i = 0; i < n; i++) {
			const ti = dtm - DRAW * i / n;
			const a = on ? sm(ti / 0.45) * fadeAll : 0;
			setAlpha(m.glyphs[i], a);
			setScale(m.glyphs[i], 1 + 0.18 * (1 - sm(ti / 0.5)));
		}
	}

	// cometa por los caminos punteados
	let cometOn = false;
	for (const c of D.comets) {
		const dtc = ((t - c.t0) % T + T) % T;
		if (dtc > c.dur + 0.4) continue;
		const p = D.paths[c.p];
		const np = p.length / 2;
		const f = Math.min(dtc / c.dur, 1);
		const vis = sm(dtc / 0.25) * (1 - sm((dtc - c.dur) / 0.4));
		const idx = f * (np - 1);
		for (let j = 0; j < D.comet.length; j++) {
			let q = Math.round(idx - j * 3);
			if (q < 0) {
				setAlpha(D.comet[j], 0);
				continue;
			}
			if (c.rev) q = np - 1 - q;
			setPos(D.comet[j], p[2 * q], p[2 * q + 1]);
			setAlpha(D.comet[j], vis * (j === 0 ? 1 : Math.pow(1 - j / D.comet.length, 1.6)) * k);
		}
		cometOn = true;
	}
	if (!cometOn) {
		for (const n of D.comet) setAlpha(n, 0);
	}

	// noche: un poco más oscuro y tranquilo
	setAlpha(D.night, mode.night ? 0.22 : 0);

	// corazones al tocar
	for (const h of taps) {
		if (h.age > h.life) continue;
		h.age += dt;
		h.x += h.vx * dt;
		h.y += h.vy * dt;
		h.vy -= 25 * dt;
		h.vx *= 1 - 0.8 * dt;
		const a = sm(h.age / 0.08) * Math.pow(Math.max(1 - h.age / h.life, 0), 1.4);
		setPos(h.n, h.x, h.y);
		setScale(h.n, h.s * (0.6 + 0.5 * sm(h.age / 0.3)));
		setAlpha(h.n, h.age > h.life ? 0 : a);
	}
	for (const f of flashes) {
		if (f.age > 0.6) continue;
		f.age += dt;
		setScale(f.n, 0.4 + 1.4 * sm(f.age / 0.6));
		setAlpha(f.n, f.age > 0.6 ? 0 : 1 - sm(f.age / 0.6));
	}
	return value;
}

export function cursorDown(event) {
	const p = event.worldPosition;
	const n = mode.valentine || mode.anniv ? 9 : 6;
	for (let i = 0; i < n; i++) {
		const h = taps[tapNext];
		tapNext = (tapNext + 1) % taps.length;
		const ang = Math.PI * (0.15 + 0.7 * Math.random());
		const sp = 90 + 140 * Math.random();
		h.x = p.x;
		h.y = p.y;
		h.vx = Math.cos(ang) * sp;
		h.vy = Math.sin(ang) * sp;
		h.s = 0.45 + 0.6 * Math.random();
		h.age = 0;
		h.life = 1.3 + 0.7 * Math.random();
	}
	const f = flashes[flashNext];
	flashNext = (flashNext + 1) % flashes.length;
	f.age = 0;
	setPos(f.n, p.x, p.y);
}

/* DropZone frontend
   Existing API:
   GET /player-info
   /api/banner/banner_UID.webp
   /api/avatar/avatar_UID.webp
   /refresh
*/

(() => {
  'use strict';

  const $ = id => document.getElementById(id);

  const state = {
    mediaUrl: '',
    bannerUrl: '',
    avatarUrl: '',
    uid: '',
    seq: 0
  };

  const HIST_KEY = 'lokaya_hist';
  const THEME_KEY = 'dropzone_theme';

  const REGIONS = {
    BD: 'Bangladesh',
    PK: 'Pakistan',
    IND: 'India',
    SG: 'Singapore',
    ME: 'Middle East',
    BR: 'Brazil',
    US: 'United States',
    NA: 'North America',
    EU: 'Europe',
    TH: 'Thailand',
    ID: 'Indonesia',
    VN: 'Vietnam',
    MY: 'Malaysia',
    TW: 'Taiwan',
    CIS: 'CIS',
    SAC: 'South America'
  };

  function fmtInt(v) {
    if (v === null || v === undefined || v === '') return '—';

    const n = Number(v);

    if (!Number.isFinite(n)) return String(v);

    return new Intl.NumberFormat().format(n);
  }

  function fmtDateTime(v) {
    if (!v) return '—';

    const d = new Date(v);

    if (Number.isNaN(d.getTime())) return String(v);

    return d.toLocaleString([], {
      dateStyle: 'medium',
      timeStyle: 'short'
    });
  }

  function fmtDate(v) {
    if (!v) return '—';

    const d = new Date(v);

    if (Number.isNaN(d.getTime())) return String(v);

    return d.toLocaleDateString([], {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  function regionName(code) {
    if (!code) return '—';

    const key = String(code).toUpperCase();

    return REGIONS[key] ? `${REGIONS[key]} (${key})` : key;
  }

  function cleanEnum(v) {
    if (v === null || v === undefined || v === '') return '—';

    return String(v)
      .replace(/_/g, ' ')
      .replace(/([a-z])([A-Z])/g, '$1 $2')
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  function set(id, value) {
    const el = $(id);

    if (!el) return;

    el.textContent =
      value === null ||
      value === undefined ||
      value === ''
        ? '—'
        : String(value);
  }

  function showError(title, message) {
    const box = $('err');

    if (!box) return;

    set('errTitle', title || 'Something went wrong');
    set('errMsg', message || 'Unable to complete the request.');

    box.hidden = false;
    box.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    });
  }

  function hideError() {
    const box = $('err');

    if (box) box.hidden = true;
  }

  function showToast(message, type = '') {
    const container = $('toastContainer');

    if (!container) return;

    const toast = document.createElement('div');

    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(8px)';

      setTimeout(() => toast.remove(), 250);
    }, 2500);
  }

  function setLoading(loading) {
    const button = $('go');

    if (!button) return;

    button.classList.toggle('loading', loading);
    button.disabled = loading;

    const loadingState = $('loadingState');

    if (loadingState) {
      loadingState.hidden = !loading;
    }
  }

  function progress(id, value, max) {
    const el = $(id);

    if (!el) return;

    const n = Number(value);
    const m = Number(max);

    if (!Number.isFinite(n) || !Number.isFinite(m) || m <= 0) {
      el.style.width = '0%';
      return;
    }

    const percent = Math.max(0, Math.min(100, (n / m) * 100));

    requestAnimationFrame(() => {
      el.style.width = `${percent}%`;
    });
  }

  async function loadBanner(url, seq) {
    if (!url) return;

    try {
      const res = await fetch(url, {
        headers: {
          Accept: 'image/webp,image/*'
        },
        cache: 'no-store'
      });

      if (!res.ok) return;

      if (seq !== state.seq) return;

      const type = res.headers.get('content-type') || '';

      if (!type.startsWith('image/')) return;

      const blob = await res.blob();

      if (seq !== state.seq) return;

      const blobUrl = URL.createObjectURL(blob);

      state.mediaUrl = blobUrl;
      state.bannerUrl = blobUrl;

      const banner = $('pBanner');

      if (banner) {
        banner.src = blobUrl;
      }
    } catch (_) {
      // Keep the fallback/source URL if available.
    }
  }

  function loadAvatar(url, seq) {
    if (!url) return;

    const img = $('src');

    if (!img) return;

    img.onload = () => {
      if (seq !== state.seq) return;
      state.avatarUrl = url;
    };

    img.onerror = () => {
      img.removeAttribute('src');
    };

    img.src = url;
  }

  function getHistory() {
    try {
      const parsed = JSON.parse(localStorage.getItem(HIST_KEY) || '[]');

      return Array.isArray(parsed) ? parsed : [];
    } catch (_) {
      return [];
    }
  }

  function pushHistory(uid) {
    if (!uid) return;

    let history = getHistory().filter(item => String(item) !== String(uid));

    history.unshift(String(uid));

    history = history.slice(0, 10);

    try {
      localStorage.setItem(HIST_KEY, JSON.stringify(history));
    } catch (_) {}

    renderHistory();
  }

  function renderHistory() {
    const box = $('histChips');

    if (!box) return;

    const history = getHistory();

    box.innerHTML = '';

    if (!history.length) {
      const empty = document.createElement('span');

      empty.style.color = 'var(--muted-2)';
      empty.style.fontSize = '10px';
      empty.textContent = 'No recent searches yet.';

      box.appendChild(empty);

      return;
    }

    history.forEach(uid => {
      const button = document.createElement('button');

      button.type = 'button';
      button.className = 'history-chip';

      const icon = document.createElement('span');

      icon.textContent = '⌕';

      const text = document.createElement('b');

      text.textContent = uid;

      button.append(icon, text);

      button.addEventListener('click', () => {
        $('uid').value = uid;

        navigate('lookup');

        $('frm').requestSubmit();
      });

      box.appendChild(button);
    });
  }

  function clearHistory() {
    try {
      localStorage.removeItem(HIST_KEY);
    } catch (_) {}

    renderHistory();

    showToast('Search history cleared', 'success');
  }

  function resetResult() {
    state.seq++;

    state.mediaUrl = '';
    state.bannerUrl = '';
    state.avatarUrl = '';
    state.uid = '';

    $('out').hidden = true;
    $('empty').hidden = false;
    $('loadingState').hidden = true;
    $('raw').hidden = true;

    hideError();

    if ($('pBanner')) $('pBanner').removeAttribute('src');
    if ($('src')) $('src').removeAttribute('src');
  }

  function fillResult(data, uid) {
    const basic = data?.basicInfo || {};
    const social = data?.socialInfo || {};
    const credit = data?.creditScoreInfo || {};
    const pet = data?.petInfo || {};
    const clan = data?.clanBasicInfo || {};
    const captain = data?.captainBasicInfo || {};
    const profile = data?.profileInfo || {};
    const diamond = data?.diamondCostRes || {};

    const region = basic.region || basic.server || data.region || 'BD';

    set('pName', basic.nickname || basic.name || 'Unknown Player');
    set('pLvl', `Level ${fmtInt(basic.level)}`);
    set('pLikes', fmtInt(basic.liked));
    set('pRegion', regionName(region));

    set(
      'pCredit',
      credit.creditScore ?? credit.score ?? '—'
    );

    set(
      'pDiamonds',
      diamond.diamondCost ?? diamond.cost ?? diamond.diamonds ?? '—'
    );

    set(
      'pSince',
      fmtDate(basic.createAt || basic.createdAt || basic.createTime)
    );

    set('cUid', basic.accountId || basic.uid || uid);
    set('cName', basic.nickname || basic.name);
    set('cLvl', basic.level);
    set('cExp', basic.exp);
    set('cRegion', regionName(region));
    set('cLikes', basic.liked);
    set('cGender', cleanEnum(social.gender));
    set('cLang', cleanEnum(social.language));
    set(
      'cMode',
      cleanEnum(
        social.preferredMode ||
        social.mode ||
        social.preferred_mode
      )
    );
    set('cBio', social.signature || social.bio);

    const brRank =
      basic.rank ||
      basic.brRank ||
      basic.battleRoyaleRank;

    const csRank =
      basic.csRank ||
      basic.clashSquadRank ||
      basic.clashSquadRankId;

    const brMax =
      basic.rankMax ||
      basic.brRankMax ||
      basic.battleRoyaleRankMax;

    const csMax =
      basic.csRankMax ||
      basic.clashSquadRankMax;

    set('rBr', brRank);
    set('rBrRank', cleanEnum(basic.rankName || basic.brRankName));
    set('rBrMax', fmtInt(brMax));

    set('rCs', csRank);
    set('rCsRank', cleanEnum(basic.csRankName || basic.clashSquadRankName));
    set('rCsMax', fmtInt(csMax));

    set(
      'rSeason',
      basic.seasonId ||
      basic.rankSeason ||
      basic.season
    );

    set(
      'rVer',
      basic.releaseVersion ||
      basic.version ||
      data.version
    );

    set(
      'rCreated',
      fmtDateTime(
        basic.createAt ||
        basic.createdAt ||
        basic.createTime
      )
    );

    set(
      'rLogin',
      fmtDateTime(
        basic.lastLoginAt ||
        basic.lastLogin ||
        basic.loginTime
      )
    );

    progress('rBrProgress', brRank, brMax);
    progress('rCsProgress', csRank, csMax);

    set(
      'lAvatar',
      profile.avatarId ||
      profile.avatar ||
      basic.avatarId
    );

    set(
      'lBanner',
      profile.bannerId ||
      profile.banner ||
      basic.bannerId
    );

    set(
      'lChar',
      profile.characterId ||
      profile.character ||
      basic.characterId
    );

    set(
      'lAwake',
      profile.awakened ||
      profile.awaken ||
      profile.awakenedCharacter
    );

    set(
      'lClothes',
      profile.clothes ||
      profile.clothesIds ||
      profile.clothing
    );

    set(
      'lSkills',
      profile.skills ||
      profile.skillIds
    );

    set(
      'lBadges',
      profile.badges ||
      profile.badgeIds
    );

    set(
      'lTitle',
      profile.title ||
      profile.titleId
    );

    set(
      'lPin',
      profile.pin ||
      profile.profilePin
    );

    set('tId', pet.id || pet.petId);
    set('tLvl', pet.level);
    set('tExp', pet.exp);
    set(
      'tSel',
      pet.isSelected ??
      pet.selected
    );
    set(
      'tSkill',
      pet.skill ||
      pet.skillName ||
      pet.skillId
    );
    set(
      'tSkin',
      pet.skin ||
      pet.skinId
    );

    set(
      'gName',
      clan.clanName ||
      clan.name ||
      'No guild data'
    );

    set(
      'gId',
      clan.clanId ||
      clan.id
    );

    set(
      'gLvl',
      clan.clanLevel ||
      clan.level
    );

    set(
      'gMem',
      clan.memberNum ||
      clan.members ||
      clan.memberCount
    );

    set(
      'gLeader',
      captain.nickname ||
      captain.name ||
      clan.captainName ||
      clan.leaderName
    );

    $('rawBody').textContent = JSON.stringify(data, null, 2);

    $('empty').hidden = true;
    $('loadingState').hidden = true;
    $('out').hidden = false;

    const bannerUrl =
      data.bannerUrl ||
      `/api/banner/banner_${encodeURIComponent(uid)}.webp?region=${encodeURIComponent(region)}`;

    const avatarUrl =
      data.avatarUrl ||
      `/api/avatar/avatar_${encodeURIComponent(uid)}.webp?region=${encodeURIComponent(region)}`;

    state.uid = uid;
    state.bannerUrl = bannerUrl;
    state.avatarUrl = avatarUrl;

    const seq = ++state.seq;

    loadBanner(bannerUrl, seq);
    loadAvatar(avatarUrl, seq);

    $('out').scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });
  }

  async function search(uid) {
    uid = String(uid || '').trim();

    if (!/^\d+$/.test(uid)) {
      showError(
        'Invalid UID',
        'Please enter a numeric Free Fire UID.'
      );

      return;
    }

    hideError();

    const seq = ++state.seq;

    setLoading(true);

    $('empty').hidden = true;
    $('out').hidden = true;

    try {
      const res = await fetch(
        `/player-info?uid=${encodeURIComponent(uid)}`,
        {
          headers: {
            Accept: 'application/json'
          },
          cache: 'no-store'
        }
      );

      let data = null;

      try {
        data = await res.json();
      } catch (_) {
        throw new Error('The server returned an invalid response.');
      }

      if (seq !== state.seq) return;

      if (!res.ok) {
        throw new Error(
          data?.message ||
          data?.error ||
          `Request failed with status ${res.status}.`
        );
      }

      if (
        data?.error ||
        data?.success === false
      ) {
        throw new Error(
          data.message ||
          data.error ||
          'Player information could not be found.'
        );
      }

      fillResult(data, uid);
      pushHistory(uid);

      showToast('Player profile loaded', 'success');

    } catch (error) {
      if (seq !== state.seq) return;

      $('empty').hidden = false;
      $('out').hidden = true;

      showError(
        'Lookup failed',
        error?.message || 'Unable to retrieve player information.'
      );

    } finally {
      if (seq === state.seq) {
        setLoading(false);
      }
    }
  }

  function downloadMedia(kind) {
    const url =
      kind === 'banner'
        ? state.bannerUrl
        : state.avatarUrl;

    if (!url) {
      showToast(`${kind === 'banner' ? 'Banner' : 'Avatar'} unavailable`, 'error');
      return;
    }

    const a = document.createElement('a');

    a.href = url;
    a.download = `dropzone-${state.uid || 'player'}-${kind}.webp`;
    a.target = '_blank';
    a.rel = 'noopener';

    document.body.appendChild(a);
    a.click();
    a.remove();

    showToast(`${kind === 'banner' ? 'Banner' : 'Avatar'} opened`, 'success');
  }

  /* -------------------------
     NAVIGATION
  ------------------------- */

  function openMenu() {
    $('sideMenu').classList.add('open');
    $('menuOverlay').classList.add('open');
    $('menuBtn').classList.add('open');

    $('menuBtn').setAttribute('aria-expanded', 'true');
    $('sideMenu').setAttribute('aria-hidden', 'false');
  }

  function closeMenu() {
    $('sideMenu').classList.remove('open');
    $('menuOverlay').classList.remove('open');
    $('menuBtn').classList.remove('open');

    $('menuBtn').setAttribute('aria-expanded', 'false');
    $('sideMenu').setAttribute('aria-hidden', 'true');
  }

  function navigate(page) {
    const validPages = ['home', 'lookup', 'support', 'api'];

    if (!validPages.includes(page)) {
      page = 'home';
    }

    document.querySelectorAll('.page').forEach(section => {
      section.classList.toggle(
        'active',
        section.dataset.pageSection === page
      );
    });

    document.querySelectorAll('[data-page]').forEach(button => {
      button.classList.toggle(
        'active',
        button.dataset.page === page
      );
    });

    history.replaceState(
      null,
      '',
      page === 'home' ? '#' : `#${page}`
    );

    closeMenu();

    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  }

  function navigateFromHash() {
    const page = location.hash.replace('#', '') || 'home';

    navigate(page);
  }

  /* -------------------------
     THEMES
  ------------------------- */

  function applyTheme(theme, notify = false) {
    const valid = [
      'midnight',
      'ocean',
      'violet',
      'sunset',
      'light'
    ];

    if (!valid.includes(theme)) {
      theme = 'midnight';
    }

    document.documentElement.dataset.theme = theme;

    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch (_) {}

    document.querySelectorAll('.theme-option').forEach(option => {
      option.classList.toggle(
        'active',
        option.dataset.themeChoice === theme
      );
    });

    if (notify) {
      const names = {
        midnight: 'Midnight theme applied',
        ocean: 'Ocean theme applied',
        violet: 'Violet theme applied',
        sunset: 'Sunset theme applied',
        light: 'Light theme applied'
      };

      showToast(names[theme], 'success');
    }
  }

  function loadTheme() {
    let theme = 'midnight';

    try {
      theme = localStorage.getItem(THEME_KEY) || 'midnight';
    } catch (_) {}

    applyTheme(theme);
  }

  function toggleThemePanel(force) {
    const panel = $('themePanel');

    if (!panel) return;

    const shouldOpen =
      typeof force === 'boolean'
        ? force
        : panel.hidden;

    panel.hidden = !shouldOpen;
  }

  /* -------------------------
     INIT
  ------------------------- */

  document.addEventListener('DOMContentLoaded', () => {
    loadTheme();
    renderHistory();

    const initialHash = location.hash.replace('#', '');

    if (
      ['home', 'lookup', 'support', 'api'].includes(initialHash)
    ) {
      navigate(initialHash);
    } else {
      navigate('home');
    }

    $('frm').addEventListener('submit', event => {
      event.preventDefault();

      search($('uid').value);
    });

    $('uid').addEventListener('input', event => {
      event.target.value = event.target.value.replace(/\D/g, '');
    });

    $('clearUid').addEventListener('click', () => {
      $('uid').value = '';
      $('uid').focus();
    });

    $('again').addEventListener('click', () => {
      resetResult();
      $('uid').focus();
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });

    $('histClear').addEventListener('click', clearHistory);

    $('errClose').addEventListener('click', hideError);

    $('dlBanner').addEventListener(
      'click',
      () => downloadMedia('banner')
    );

    $('dlAvatar').addEventListener(
      'click',
      () => downloadMedia('avatar')
    );

    $('rawToggle').addEventListener('click', () => {
      const raw = $('raw');

      raw.hidden = !raw.hidden;

      if (!raw.hidden) {
        raw.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });

    $('rawCopy').addEventListener('click', async () => {
      const text = $('rawBody').textContent;

      try {
        await navigator.clipboard.writeText(text);

        $('rawCopyTxt').textContent = 'Copied!';

        showToast('JSON copied to clipboard', 'success');

        setTimeout(() => {
          $('rawCopyTxt').textContent = 'Copy JSON';
        }, 1500);

      } catch (_) {
        showToast('Could not copy JSON', 'error');
      }
    });

    $('menuBtn').addEventListener('click', () => {
      if ($('sideMenu').classList.contains('open')) {
        closeMenu();
      } else {
        openMenu();
      }
    });

    $('closeMenu').addEventListener('click', closeMenu);
    $('menuOverlay').addEventListener('click', closeMenu);

    document.querySelectorAll('[data-page]').forEach(button => {
      button.addEventListener('click', () => {
        navigate(button.dataset.page);
      });
    });

    $('themeBtn').addEventListener('click', () => {
      toggleThemePanel();
    });

    $('menuTheme').addEventListener('click', () => {
      closeMenu();
      toggleThemePanel(true);
    });

    $('themeClose').addEventListener('click', () => {
      toggleThemePanel(false);
    });

    document.querySelectorAll('.theme-option').forEach(option => {
      option.addEventListener('click', () => {
        applyTheme(
          option.dataset.themeChoice,
          true
        );

        setTimeout(() => {
          toggleThemePanel(false);
        }, 250);
      });
    });

    window.addEventListener('hashchange', navigateFromHash);

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        closeMenu();
        toggleThemePanel(false);
      }
    });
  });

})();

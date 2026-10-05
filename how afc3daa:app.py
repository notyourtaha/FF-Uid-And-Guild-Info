[1mdiff --git a/app.py b/app.py[m
[1mindex c9d87f4..0455173 100644[m
[1m--- a/app.py[m
[1m+++ b/app.py[m
[36m@@ -97,11 +97,33 @@[m [masync def create_jwt(region: str):[m
     }[m
 [m
 async def initialize_tokens():[m
[31m-    tasks = [create_jwt(r) for r in SUPPORTED_REGIONS][m
[31m-    results = await asyncio.gather(*tasks, return_exceptions=True)[m
[31m-    failed = sum(isinstance(result, Exception) for result in results)[m
[32m+[m[32m    results = {}[m
[32m+[m
[32m+[m[32m    # Authenticate sequentially instead of hammering MajorLogin[m
[32m+[m[32m    # with many simultaneous requests.[m
[32m+[m[32m    for region in SUPPORTED_REGIONS:[m
[32m+[m[32m        try:[m
[32m+[m[32m            await create_jwt(region)[m
[32m+[m[32m            results[region] = True[m
[32m+[m[32m            print(f"[✓] Token ready: {region}")[m
[32m+[m[32m            await asyncio.sleep(1.0)[m
[32m+[m[32m        except Exception as exc:[m
[32m+[m[32m            results[region] = exc[m
[32m+[m[32m            print(f"[!] Token failed: {region} -> {exc}")[m
[32m+[m
[32m+[m[32m    failed = sum(value is not True for value in results.values())[m
[32m+[m
[32m+[m[32m    if failed == len(results):[m
[32m+[m[32m        raise UpstreamError([m
[32m+[m[32m            'TOKEN_REFRESH_FAILED',[m
[32m+[m[32m            'No regional tokens could be created.',[m
[32m+[m[32m            503[m
[32m+[m[32m        )[m
[32m+[m
     if failed:[m
[31m-        raise UpstreamError('TOKEN_REFRESH_INCOMPLETE', f'{failed} regional token refreshes failed; successful tokens remain available.', 503)[m
[32m+[m[32m        print(f"[WARN] {failed}/{len(results)} regional tokens failed.")[m
[32m+[m[32m    else:[m
[32m+[m[32m        print(f"[✓] All {len(results)} regional tokens initialized.")[m
 [m
 def start_token_refresher():[m
     def _loop():[m

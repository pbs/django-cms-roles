CHANGELOG
=========

Revision 861700f (06.11.2018, 09:39 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Pin pytest 3.4.0 and pytest-django 3.1.2

Revision 48e8854 (18.10.2016, 07:41 UTC)
----------------------------------------

* LUN-3289

  * Implement interface for filer rights check.

No other commits.

Revision 9494631 (01.04.2016, 06:48 UTC)
----------------------------------------

* LUN-2817

  * Deny access to UserSetup change_form.

* LUN-2917

  * Document UserSetupAdmin workaround.

No other commits.

Revision 75f8466 (01.10.2015, 12:21 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Add missing migration 0002.

Revision a1735b8 (23.09.2015, 15:32 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Django 1.8: updated extra context for admin view.
  * Django 1.8 upgrade: removed some django1.9 deprecation warnings
  * Django 1.8 upgrade: updated settings & versions. fixed select_related call

Revision bb049f1 (11.09.2015, 13:59 UTC)
----------------------------------------

* LUN-2620

  * added icons to buttons on user setup form

No other commits.

Revision aff4570 (04.09.2015, 09:03 UTC)
----------------------------------------

* LUN-2596

  * left align form

No other commits.

Revision 0ae451d (28.08.2015, 07:21 UTC)
----------------------------------------

* LUN-2310

  * checkout the admin.py file since it has no updates
  * remaining of flag for Ace theme
  * flag created for keeping the default look of the form if Ace theme is not activated
  * user setup page updated
  * breadcrumbs updated

No other commits.

Revision b5005c8 (17.07.2015, 13:29 UTC)
----------------------------------------

No new issues.

* Misc commits

  * tox: Don't allow django 1.8 prereleases
  * Django 1.7 upgrade: fixed usersetup 'model' to not generate table
  * s3sourceuploader no longer required
  * django 1.7 upgrade: generated new migrations; fixed tests and deprecation warnings
  * Django 1.6 upghrade: fixed imports & admin media tag

Revision ef03251 (04.06.2015, 17:09 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Changed version to one that describes this as a pbs fork

Revision b184c57 (23.04.2015, 15:37 UTC)
----------------------------------------

No new issues.

* Misc commits

  * parse no longer needed

Revision 10fdd5b (13.01.2015, 09:35 UTC)
----------------------------------------

* LUN-1963

  * souldn't fetch pages when user or role is missing

No other commits.

Revision 756a603 (17.07.2014, 14:51 UTC)
----------------------------------------

* LUN-1563

  * re-added the group_name regex pattern back as a member of the Role class, because it is used in tests
  * simplified the logic of group name generation
  * delete unused import
  * Make sure the auto-generated site permission does not exceed the max length of the DB field

* Misc commits

  * bumb version as instructedd by bamboo

Revision 74407a0 (17.04.2014, 13:18 UTC)
----------------------------------------

Changelog history starts here.

Macro development
==================

Basic workflow
--------------

#. Open the KLayout application
#. From the top menu, choose "Macros" and "Macro Development"
#. Select "Python"
#. Open "[Local - python branch]", where you should see the kqcircuits directory
#. Open ``kqcircuits/macros/generate/M001``
#. Click on the green play symbol with the exclamation mark ("Run script
   from the current tab")
#. A circular shape with an array of squares inside should appear in the
   main KLayout window


Tips and basics for Beginners
-----------------------------

#. Read the terminology.
#. Locate the ``mask.lym`` and ``placing_a_pcell.lym`` tutorials
   under *kqcircuits -> macros -> examples* directory. Use the tutorials to
   have basic understanding about KLayout Editor and macro generation
   concept.
#. Read the documentation of KLayout on it's website and here is a list
   of the most important and widely used classes that you may have
   benefit starting to practice first.

    #. Application
    #. Cell
    #. CellView
    #. DBox
    #. DPath
    #. DPoint
    #. DPolygon
    #. DTrans
    #. DVector
    #. DCellInstArray
    #. Instance
    #. LayerInfo
    #. Layout
    #. LayoutView
    #. MainWindow
    #. PCellDecleration
    #. Region
    #. Shape
    #. Shapes

#. To run a macro file, you can either use Shift+F5 or you can locate
   the green play symbol with an exclamation mark on it's right side.
#. Even though you ran a particular macro file, if nothing happens
   inside the KLayout Editor and the screen is empty; it is highly
   likely that there is an error during the generation of the macro. The
   best thing to do when this happens is to run the kqcircuit.py file to
   see if there is an error log that makes it easier to track the error.
#. If there is an error log that appeared during the generation of the
   macro, but the log is difficult to track, it may again be very useful
   to run kqcircuit file to see if there is a log that makes it easier
   to track the file and line that contains the error.
#. Sometimes the generation of the macro is complete and there appears
   to be no error on the KLayout IDE, but when you check the Editor, you
   may see that parts of the cell are missing. In this case, it is very
   likely that there are error logs located inside the cells that
   contains the error. This error logs contain the information about
   which file and which line is problematic and it's very useful to be
   aware of.
#. Even though you have changed some line inside a PCell file, if
   nothing changes on the generated design inside the editor, you should
   know that you have to re-run the ``reload.lym`` file to be able to reload
   the library features for changes to be updated.
#. KLayout may crash if you try to run ``reload.lym`` file after generating a
   macro. This is a problem that needs to be fixed. If
   this kind of crash happens, you should re-launch the KLayout Editor.
